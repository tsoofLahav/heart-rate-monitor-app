import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'package:audioplayers/audioplayers.dart';

class BiofeedbackScreen extends StatefulWidget {
  final String mode;
  BiofeedbackScreen({required this.mode});

  @override
  _BiofeedbackScreenState createState() => _BiofeedbackScreenState();
}

class _BiofeedbackScreenState extends State<BiofeedbackScreen> {
  CameraController? _cameraController;
  bool _isRecording = false;
  int _bpm = 0;
  bool _unstableReading = false;
  bool _loading = false;
  bool _serverError = false;
  final AudioPlayer _audioPlayer = AudioPlayer();
  Map<String, dynamic>? _nextResponse;
  int _sessionId = 0;
  List<double> _timeIntervals = [];
  int _playbackReferenceTime = 0;

  @override
  void initState() {
    super.initState();
    _initCamera();
    _startSession();
  }

  Future<void> _startSession() async {
    final uri = Uri.parse("https://backappmonitor-gwhubscvb6bab4hq.israelcentral-01.azurewebsites.net/data/start_session");
    try {
      final response = await http.post(uri);
      if (response.statusCode == 200) {
        final jsonResponse = json.decode(response.body);
        _sessionId = jsonResponse['session_id'] ?? 0;
        print("📡 Session started with ID: $_sessionId");
      }
    } catch (e) {
      print("❌ Failed to start session: $e");
    }
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    final backCamera = cameras.firstWhere((camera) => camera.lensDirection == CameraLensDirection.back);

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
    await _cameraController!.setFlashMode(FlashMode.torch);

    setState(() {});
  }

  Future<void> _startBiofeedback() async {
    _isRecording = true;
    _runCycle();
    setState(() {});
  }

  Future<void> _runCycle() async {
    while (_isRecording) {
      await _cameraController!.startVideoRecording();
      final peakPlayback = _playPeaks(_timeIntervals);
      await Future.delayed(Duration(seconds: 5));
      await _runBreak();
      await peakPlayback;
    }
  }

  Future<void> _runBreak() async {
    final int breakStart = DateTime.now().millisecondsSinceEpoch;
    _playbackReferenceTime = breakStart;
    try {
      final file = await _stopRecording();
      await _sendVideoToBackend(file);
      if (_nextResponse != null) {
        _handleBackendResponse(_nextResponse!);
        _nextResponse = null;
      }
    } catch (e) {
      print("⚠️ Break error: $e");
    }
    final int breakEnd = DateTime.now().millisecondsSinceEpoch;
    final int breakDuration = breakEnd - breakStart;
    print("🔧 Break duration: $breakDuration ms");
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

  Future<void> _sendVideoToBackend(String filePath) async {
    var uri = Uri.parse("https://backappmonitor-gwhubscvb6bab4hq.israelcentral-01.azurewebsites.net/process_video");
    var request = http.MultipartRequest('POST', uri);
    request.files.add(await http.MultipartFile.fromPath('video', filePath));
    request.send().then((response) async {
      if (response.statusCode == 200) {
        var jsonResponse = await response.stream.bytesToString();
        _nextResponse = json.decode(jsonResponse);
      }
    }).catchError((e) {
      print("❌ Error sending video: $e");
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
    if (data.containsKey("bpm") && data.containsKey("prediction")) {
      setState(() {
        _bpm = data["bpm"].toInt();
        _timeIntervals = List<double>.from(data["prediction"]);
      });
    }
  }

  Future<void> _playPeaks(List<double> peaks) async {
    final int referenceTime = _playbackReferenceTime;
    List<Future<void>> tasks = [];

    for (double peak in peaks) {
      int targetTime = referenceTime + (peak * 1000).toInt();
      int delay = targetTime - DateTime.now().millisecondsSinceEpoch;

      if (delay <= 0) {
        await _audioPlayer.play(AssetSource('boom.wav'));
        print("🔔 Played immediately at \${DateTime.now().millisecondsSinceEpoch - referenceTime} ms");
      } else {
        tasks.add(Future.delayed(Duration(milliseconds: delay), () async {
          await _audioPlayer.play(AssetSource('boom.wav'));
          print("🔔 Played at \${DateTime.now().millisecondsSinceEpoch - referenceTime} ms");
        }));
      }
    }

    await Future.wait(tasks);
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
      await _endSession();
      setState(() {});
    }
  }

  Future<void> _endSession() async {
    final uri = Uri.parse("https://backappmonitor-gwhubscvb6bab4hq.israelcentral-01.azurewebsites.net/data/end_session");
    try {
      await http.post(uri, body: json.encode({"session_id": _sessionId}), headers: {"Content-Type": "application/json"});
      print("✅ Session ended");
    } catch (e) {
      print("❌ Failed to end session: $e");
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
    else if (_bpm > 0) message = "BPM: \$_bpm";

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
