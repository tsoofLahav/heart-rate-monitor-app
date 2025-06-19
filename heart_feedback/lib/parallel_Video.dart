// Updated version of BiofeedbackScreen with clean state machine, dual players, and backend cancellation

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
  bool _isStopping = false;
  bool _unstable = false;
  bool _serverError = false;
  int _bpm = 0;
  File? _nextAudioFile;
  AudioPlayer? _player1;
  AudioPlayer? _player2;
  bool _useFirstPlayer = true;
  int _lastRequestTime = 0;
  Timer? _loadingTimer;
  double _loadingProgress = 0.0;
  bool _isLoadingAnimationRunning = false;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    final backCamera = cameras.firstWhere((c) => c.lensDirection == CameraLensDirection.back);
    _cameraController = CameraController(backCamera, ResolutionPreset.medium, enableAudio: false, imageFormatGroup: ImageFormatGroup.yuv420);
    await _cameraController!.initialize();
    setState(() {});
  }

  Future<void> _startBiofeedback() async {
    _isStopping = false;
    _bpm = 0;
    _unstable = false;
    _serverError = false;
    _nextAudioFile = null;
    _startLoadingAnimation();

    await http.get(Uri.parse('https://myheartapp-frcvaecxddehf6gm.israelcentral-01.azurewebsites.net/load_models'));
    await _cameraController!.setFlashMode(FlashMode.torch);
    _isRunning = true;
    _runCycle();
  }

  Future<void> _runCycle() async {
    while (_isRunning && !_isStopping) {
      // Play audio early (begins before next recording)
      if (_nextAudioFile != null) {
        final player = _useFirstPlayer ? (_player1 = AudioPlayer()) : (_player2 = AudioPlayer());
        _useFirstPlayer = !_useFirstPlayer;
        player.play(DeviceFileSource(_nextAudioFile!.path));
        SessionDataManager().addAudioStartSignal(valid: true);
        _nextAudioFile = null;
      } else {
        SessionDataManager().addAudioStartSignal(valid: false);
      }

      // State 1: Record 3 sec
      await _cameraController!.startVideoRecording();
      await Future.delayed(Duration(seconds: 3));

      XFile? file;
      if (_cameraController!.value.isRecordingVideo) {
        file = await _cameraController!.stopVideoRecording();
      }

      // State 2: Break + backend request
      if (file != null) {
        final requestTime = DateTime.now().millisecondsSinceEpoch;
        _lastRequestTime = requestTime;
        _sendToBackend(file.path, requestTime);
      }

      await Future.delayed(Duration(milliseconds: 490));
    }
  }

  Future<void> _sendToBackend(String filePath, int requestTime) async {
    if (_isStopping) return;

    final request = http.MultipartRequest('POST', Uri.parse('https://myheartapp-frcvaecxddehf6gm.israelcentral-01.azurewebsites.net/process_video'));
    request.files.add(await http.MultipartFile.fromPath('video', filePath));

    try {
      final response = await request.send();
      if (_isStopping || requestTime != _lastRequestTime) return;

      final contentType = response.headers['content-type'];
      if (contentType != null && contentType.contains('audio/wav')) {
        final audioBytes = await response.stream.toBytes();
        final bpmHeader = response.headers['x-bpm'];

        final tempDir = await getTemporaryDirectory();
        final savePath = '${tempDir.path}/next.wav';
        final file = await File(savePath).writeAsBytes(audioBytes);

        if (!mounted || _isStopping) return;
        setState(() {
          _nextAudioFile = file;
          _bpm = double.tryParse(bpmHeader ?? '')?.toInt() ?? 0;
        });
      } else {
        final text = await response.stream.bytesToString();
        final data = json.decode(text);

        if (!mounted || _isStopping || requestTime != _lastRequestTime) return;
        setState(() {
          _serverError = data['server_error'] == true;
          _unstable = data['not_reading'] == true;
          if (_serverError || _unstable) _bpm = 0;
        });
      }
    } catch (e) {
      print("❌ Backend error: $e");
    }
  }

  Future<void> _stopBiofeedback() async {
    _isStopping = true;
    _isRunning = false;
    _discardResources();
    await _cameraController?.setFlashMode(FlashMode.off);

    try {
      final response = await http.post(Uri.parse('https://myheartapp-frcvaecxddehf6gm.israelcentral-01.azurewebsites.net/end'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        SessionDataManager().saveSessionData(data);
      }
    } catch (e) {
      print("❌ Failed to end session: $e");
    }

    if (!mounted) return;
    setState(() {});
  }

  void _discardResources() {
    _player1?.stop();
    _player2?.stop();
    _player1?.dispose();
    _player2?.dispose();
    _player1 = null;
    _player2 = null;
    _loadingTimer?.cancel();
    _loadingProgress = 0.0;
    _isLoadingAnimationRunning = false;
  }

  @override
  void dispose() {
    _isRunning = false;
    _isStopping = true;
    _discardResources();
    _cameraController?.dispose();
    super.dispose();
  }

  void _startLoadingAnimation() {
    if (_isLoadingAnimationRunning) return;
    _isLoadingAnimationRunning = true;
    _loadingProgress = 0.0;
    _loadingTimer?.cancel();

    const duration = Duration(milliseconds: 100);
    final int totalSteps = (9500 / duration.inMilliseconds).round();

    _loadingTimer = Timer.periodic(duration, (timer) {
      if (!mounted || _isStopping) {
        timer.cancel();
        return;
      }
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
  Widget build(BuildContext context) {
    String message;
    if (_isStopping) {
      message = "finished";
    } else if (_serverError) {
      message = "Error, restart app";
    } else if (_unstable) {
      message = "Unstable, stay steady";
    } else if (_bpm > 0) {
      message = "BPM: $_bpm";
    } else if (_isRunning) {
      message = "Loading...";
    } else {
      message = "Cover lens gently with finger and press Start";
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
          _isRunning && _isLoadingAnimationRunning
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
                    Text("Loading...", style: TextStyle(color: Colors.white, fontSize: 16)),
                  ],
                )
              : Text(
                  message,
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: _serverError ? Colors.red : Colors.white),
                  textAlign: TextAlign.center,
                ),
          SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ElevatedButton(onPressed: _isRunning ? null : _startBiofeedback, child: Text('Play')),
              SizedBox(width: 20),
              ElevatedButton(onPressed: _isRunning ? _stopBiofeedback : null, child: Text('Stop')),
            ],
          ),
        ],
      ),
    );
  }
}
