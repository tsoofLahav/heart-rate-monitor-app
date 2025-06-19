import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'package:audioplayers/audioplayers.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';
import 'session_data_manager.dart';

class BiofeedbackScreen extends StatefulWidget {
  final String mode;
  BiofeedbackScreen({required this.mode});

  @override
  _BiofeedbackScreenState createState() => _BiofeedbackScreenState();
}

class _BiofeedbackScreenState extends State<BiofeedbackScreen> {
  CameraController? _cameraController;
  bool _isRunning = false;
  bool _loading = false;
  bool _unstable = false;
  bool _serverError = false;
  int _bpm = 0;
  double _loadingProgress = 0.0;
  Timer? _loadingTimer;
  bool _isLoadingAnimationRunning = false;
  File? _nextAudioFile;
  bool _connectionTimeout = false;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    final backCamera = cameras.firstWhere((c) => c.lensDirection == CameraLensDirection.back);
    _cameraController = CameraController(backCamera, ResolutionPreset.medium,
        enableAudio: false, imageFormatGroup: ImageFormatGroup.yuv420);
    await _cameraController!.initialize();
    setState(() {});
  }

  Future<void> _startBiofeedback() async {
    await http.get(Uri.parse('https://myheartapp-frcvaecxddehf6gm.israelcentral-01.azurewebsites.net/load_models'));
    await _cameraController!.setFlashMode(FlashMode.torch);
    _isRunning = true;
    setState(() {
      _loading = true;
      _startLoadingAnimation();
    });
    _runCycle();
  }

  Future<void> _stopBiofeedback() async {
    _isRunning = false;
    if (_cameraController?.value.isRecordingVideo == true) {
      await _cameraController!.stopVideoRecording();
    }
    await _cameraController?.setFlashMode(FlashMode.off);

    try {
      final response = await http.post(Uri.parse('https://myheartapp-frcvaecxddehf6gm.israelcentral-01.azurewebsites.net/end'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        SessionDataManager().saveSessionData(data);
      } else {
        print("❌ Backend end session error: ${response.statusCode}");
      }
    } catch (e) {
      print("❌ Failed to end session: $e");
    }

    setState(() {
      _loading = false;
      _serverError = false;
      _unstable = false;
      _loadingProgress = 0.0;
      _isLoadingAnimationRunning = false;
    });
  }


  Future<void> _runCycle() async {
    while (_isRunning) {
      await _cameraController!.startVideoRecording();

      // Play next audio if available
      if (_nextAudioFile != null) {
        try {
          SessionDataManager().addAudioStartSignal(valid: true);
          final player = AudioPlayer();
          await player.play(DeviceFileSource(_nextAudioFile!.path));
        } catch (e) {
          print("\u274c Audio playback failed: $e");
        }
        _nextAudioFile = null;
      } else {
        SessionDataManager().addAudioStartSignal(valid: false);
      }

      await Future.delayed(Duration(seconds: 3));

      XFile? file;
      if (_cameraController!.value.isRecordingVideo) {
        file = await _cameraController!.stopVideoRecording();
      }

      if (file != null) {
        _sendToBackend(file.path);
      }

      await Future.delayed(Duration(milliseconds: 500));
    }
  }

  Future<void> _sendToBackend(String filePath) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('https://myheartapp-frcvaecxddehf6gm.israelcentral-01.azurewebsites.net/process_video'),
    );
    request.files.add(await http.MultipartFile.fromPath('video', filePath));

    final startTime = DateTime.now().millisecondsSinceEpoch;
    print("📤 Sent to backend at $startTime");

    bool responded = false;

    Future.delayed(const Duration(milliseconds: 480), () {
      if (!responded) {
        setState(() {
          _connectionTimeout = true;
        });
        _stopBiofeedback();
      }
    });

    try {
      final response = await request.send();
      responded = true;

      final endTime = DateTime.now().millisecondsSinceEpoch;
      print("📥 Response received at $endTime");
      print("⏱️ Total round-trip time: ${endTime - startTime} ms");

      final contentType = response.headers['content-type'];

      if (contentType != null && contentType.contains('audio/wav')) {
        final audioBytes = await response.stream.toBytes();
        final bpmHeader = response.headers['x-bpm'];

        final tempDir = await getTemporaryDirectory();
        final savePath = '${tempDir.path}/next.wav';
        final file = await File(savePath).writeAsBytes(audioBytes);

        setState(() {
          _nextAudioFile = file;
          _bpm = double.tryParse(bpmHeader ?? '')?.toInt() ?? 0;
          _loading = false;
          _connectionTimeout = false; // clear if success
        });
      } else {
        final text = await response.stream.bytesToString();
        final data = json.decode(text);

        setState(() {
          _loading = data['loading'] == true;
          _serverError = data['server_error'] == true;
          _unstable = data['not_reading'] == true;
          _isLoadingAnimationRunning = !_loading;
          _connectionTimeout = false;
        });
      }
    } catch (e) {
      print("\u274c Backend error: $e");
    }
  }


  void _startLoadingAnimation() {
    if (_isLoadingAnimationRunning) return;
    _isLoadingAnimationRunning = true;
    _loadingProgress = 0.0;
    _loadingTimer?.cancel();

    const duration = Duration(milliseconds: 100);
    final int totalSteps = (9500 / duration.inMilliseconds).round();

    _loadingTimer = Timer.periodic(duration, (timer) {
      setState(() {
        _loadingProgress += 1.0 / totalSteps;
        if (_loadingProgress >= 1.0) {
          _loadingProgress = 1.0;
          _isLoadingAnimationRunning = false;
          timer.cancel();
        }
      });
    });
  }


  @override
  void dispose() {
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    String message;

    if (_connectionTimeout) {
      message = "Internet not stable enough";
    } else if (_serverError) {
      message = "Error, restart app";
    } else if (_unstable) {
      message = "Unstable, starting over, please hold still";
    } else if (_bpm > 0) {
      message = "BPM: $_bpm";
    } else {
      message = "Put finger on camera gently and press Start";
    }

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: Text('Biofeedback')),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(height: 40),
          ClipOval(
            child: SizedBox(
              width: 150,
              height: 150,
              child: _cameraController?.value.isInitialized == true
                  ? CameraPreview(_cameraController!)
                  : CircularProgressIndicator(),
            ),
          ),
          SizedBox(height: 80),
          _isRunning && _loading
              ? Column(
                  children: [
                    SizedBox(
                      width: 60,
                      height: 60,
                      child: CircularProgressIndicator(
                        value: _loadingProgress,
                        strokeWidth: 6,
                        color: Colors.green,
                      ),
                    ),
                    SizedBox(height: 12),
                    Text(
                      "Loading...",
                      style: TextStyle(color: Colors.white, fontSize: 16),
                    ),
                  ],
                )
              : Text(
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
                onPressed: _isRunning ? null : _startBiofeedback,
                child: Text('Play'),
              ),
              SizedBox(width: 20),
              ElevatedButton(
                onPressed: _isRunning ? _stopBiofeedback : null,
                child: Text('Stop'),
              ),
            ],
          ),
        ],
      ),
    );
  }

}
