// Full refactored code based on your original with structure and timing logs
// Divided into: feedback loop, recording loop, break logic, and UI
// Keeps original content and adds structure + logs

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:audioplayers/audioplayers.dart';
import 'guessing_screen.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'dart:io';


class BiofeedbackScreen extends StatefulWidget {
  final String mode;
  BiofeedbackScreen({required this.mode});

  @override
  _BiofeedbackScreenState createState() => _BiofeedbackScreenState();
}

class _BiofeedbackScreenState extends State<BiofeedbackScreen> {
  CameraController? _cameraController;
  bool _isRecording = false;
  List<double> _timeIntervals = [];
  int _bpm = 0;
  bool _unstableReading = false;
  bool _loading = false;
  bool _serverError = false;
  final AudioPlayer _audioPlayer = AudioPlayer();
  Future<Map<String, dynamic>>? _previousResponse;
  Map<String, dynamic>? _nextResponse;
  int _sessionId = 0;
  int lastPlaybackStartMillis = DateTime.now().millisecondsSinceEpoch;

  Future<String> getDeviceSource() async {
    final deviceInfo = DeviceInfoPlugin();

    if (Platform.isAndroid) {
      final info = await deviceInfo.androidInfo;
      return "android_${info.model}_${info.id}";
    } else if (Platform.isIOS) {
      final info = await deviceInfo.iosInfo;
      return "ios_${info.name}_${info.identifierForVendor}";
    } else {
      return "unknown_device";
    }
  }


  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    final backCamera = cameras.firstWhere(
        (camera) => camera.lensDirection == CameraLensDirection.back);

    _cameraController = CameraController(
      backCamera,
      ResolutionPreset.medium,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.yuv420,
    );

    await _cameraController!.initialize();
    await _cameraController!.setExposureMode(ExposureMode.auto);
    await _cameraController!.setFocusMode(FocusMode.auto);
    await _cameraController!.lockCaptureOrientation();

    setState(() {});
  }

  Future<void> _startBiofeedback() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;
    await _createNewSession();
    if (_sessionId == 0) return;
    _isRecording = true;
    _runCycle();
    setState(() {});
  }

  Future<void> _createNewSession() async {
    final source = await getDeviceSource();

    var url = Uri.parse("https://monitorflaskbackend-aaadajegfjd7b9hq.israelcentral-01.azurewebsites.net/start_session");
    var response = await http.post(
      url,
      headers: {"Content-Type": "application/json"},
      body: json.encode({"source": source}),
    );

    if (response.statusCode == 200) {
      var jsonResponse = json.decode(response.body);
      setState(() => _sessionId = jsonResponse["session_id"]);
    } else {
      print("❌ Failed to create session: ${response.body}");
    }
  }


  Future<void> _runCycle() async {
    while (_isRecording) {
      final int cycleStart = DateTime.now().millisecondsSinceEpoch;
      _recordingLoop();
      _feedbackLoop();
      await Future.delayed(Duration(seconds: 5));
      await _runBreak();
      final int cycleEnd = DateTime.now().millisecondsSinceEpoch;
      print("⏱️ Full cycle time: ${cycleEnd - cycleStart} ms");
    }
  }

  Future<void> _runBreak() async {
    final int breakStart = DateTime.now().millisecondsSinceEpoch;
    try {
      final file = await _stopRecording();
      _sendVideoToBackend(file);
      if (_nextResponse != null) {
        _handleBackendResponse(_nextResponse!);
        _nextResponse = null;
      }
    } catch (e) {
      print("⚠️ Break error: $e");
    }
    final int breakEnd = DateTime.now().millisecondsSinceEpoch;
    print("🔧 Break duration: ${breakEnd - breakStart} ms");
  }

  Future<void> _recordingLoop() async {
    try {
      await _cameraController!.setFlashMode(FlashMode.torch);
      await _cameraController!.startVideoRecording();
    } catch (e) {
      print("🎥 Error starting recording: $e");
    }
  }

  Future<String> _stopRecording() async {
    try {
      final XFile file = await _cameraController!.stopVideoRecording();
      return file.path;
    } catch (e) {
      print("❌ Error stopping video: $e");
      rethrow;
    }
  }

  void _sendVideoToBackend(String filePath) {
    var uri = Uri.parse("https://monitorflaskbackend-aaadajegfjd7b9hq.israelcentral-01.azurewebsites.net/process_video");
    var request = http.MultipartRequest('POST', uri);
    http.MultipartFile.fromPath('video', filePath).then((file) {
      request.files.add(file);
      final sentAt = DateTime.now().millisecondsSinceEpoch;
      _previousResponse = request.send().then<Map<String, dynamic>>((response) async {
        final receivedAt = DateTime.now().millisecondsSinceEpoch;
        print("📨 Response received after ${receivedAt - sentAt} ms");
        if (response.statusCode == 200) {
          var jsonResponse = await response.stream.bytesToString();
          _nextResponse = json.decode(jsonResponse);
        }
        return {};
      }).catchError((e) {
        print("❌ Error sending video: $e");
        return <String, dynamic>{};
      });
    });
  }

  void _handleBackendResponse(Map<String, dynamic> data) {
    setState(() {
      _loading = false;
      _serverError = false;
      _unstableReading = false;
    });

    if (data.containsKey("server_error")) {
      setState(() => _serverError = true);
      return;
    }
    if (data.containsKey("loading")) {
      setState(() => _loading = true);
      return;
    }
    if (data.containsKey("not_reading")) {
      setState(() => _unstableReading = data["not_reading"]);
      return;
    }
    if (data.containsKey("bpm") && data.containsKey("intervals")) {
      setState(() {
        _bpm = data["bpm"].toInt();
        _timeIntervals = List<double>.from(data["intervals"])
            .map((interval) => (interval - 0.05).clamp(0.0, double.infinity))
            .toList();
      });
    }
  }

  Future<void> _feedbackLoop() async {
    if (_timeIntervals.length < 2) return;

    int playbackStart = DateTime.now().millisecondsSinceEpoch;
    await Future.delayed(Duration(milliseconds: (_timeIntervals[0] * 1000).toInt()));

    for (int i = 1; i < _timeIntervals.length - 1; i++) {
      int now = DateTime.now().millisecondsSinceEpoch;
      print("🔔 Beat $i at ${now - playbackStart} ms");
      await _audioPlayer.play(AssetSource('boom.wav'));
      await Future.delayed(Duration(milliseconds: (_timeIntervals[i] * 1000).toInt()));
    }
  }


  Future<void> _stopBiofeedback() async {
    if (_isRecording) {
      _isRecording = false;
      try {
        await _cameraController!.stopVideoRecording();
      } catch (e) {
        print("Error stopping video recording: $e");
      }
      await _cameraController!.setFlashMode(FlashMode.off);
      setState(() {});
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => GuessingScreen(sessionId: _sessionId)),
      );
    }
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    String message = "Place finger on camera";
    if (_loading) message = "Loading...";
    else if (_serverError) message = "Error, please restart the app or ask for support";
    else if (_unstableReading) message = "Please don't move/ place your finger";
    else if (_bpm > 0) message = "BPM: $_bpm";

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: Text('Biofeedback Screen')),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(height: 40),
          ClipOval(
            child: SizedBox(
              width: 150,
              height: 150,
              child: _cameraController != null && _cameraController!.value.isInitialized
                  ? CameraPreview(_cameraController!)
                  : CircularProgressIndicator(),
            ),
          ),
          SizedBox(height: 80),
          Text(
            message,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: _serverError ? Colors.red : Colors.white,
            ),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ElevatedButton(
                onPressed: _isRecording ? null : _startBiofeedback,
                child: Text('Play'),
              ),
              SizedBox(width: 20),
              ElevatedButton(
                onPressed: _isRecording ? _stopBiofeedback : null,
                child: Text('Stop'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
