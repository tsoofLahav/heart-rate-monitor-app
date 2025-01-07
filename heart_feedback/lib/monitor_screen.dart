import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'camera_service.dart';
import 'backend_service.dart';
import 'audio_service.dart';
import 'dart:async';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

class HeartRateMonitor extends StatefulWidget {
  @override
  _HeartRateMonitorState createState() => _HeartRateMonitorState();
}

class _HeartRateMonitorState extends State<HeartRateMonitor> {
  final CameraService _cameraService = CameraService();
  final BackendService _backendService = BackendService();
  final AudioService _audioService = AudioService();

  CameraController? _cameraController;
  double _displayedHeartRate = 0.0;
  bool _isRecording = false;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    WidgetsFlutterBinding.ensureInitialized();
    List<CameraDescription> cameras = await availableCameras();
    print("Available cameras: $cameras");
    _cameraController = await _cameraService.initializeCamera(cameras);
    if (_cameraController?.value.isInitialized == true) {
      print("Camera successfully initialized.");
      setState(() {});
    } else {
      print("Camera initialization failed.");
    }
  }

  Future<void> _startRecording() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      print("Camera is not initialized. Cannot start recording.");
      return;
    }

    setState(() => _isRecording = true);
    print("Started recording process.");

    final directory = await getApplicationDocumentsDirectory();

    try {
      // Start the first recording
      print("Starting initial video recording...");
      await _cameraController!.startVideoRecording();
      print("Initial recording started successfully.");

      while (_isRecording) {
        final videoPath = '${directory.path}/heart_rate_video_${DateTime.now().millisecondsSinceEpoch}.mp4';

        // Stop the current recording
        print("Stopping video recording...");
        XFile videoFile = await _cameraController!.stopVideoRecording();
        print("Recording stopped. Video saved at: ${videoFile.path}");

        // Process the video file
        File newFile = await File(videoFile.path).copy(videoPath);
        print("File copied to: $videoPath");

        // Send to backend
        var result = await _backendService.sendVideoToBackend(newFile);
        if (result != null) {
          print("Backend response received: $result");
          _audioService.processPeaks(result['peaks'], result['newStart']);
          setState(() {
            _displayedHeartRate = result['heart_rate'] ?? 0.0;
          });
        } else {
          print("Backend returned null.");
        }

        // Start the next recording
        print("Starting new video recording...");
        await _cameraController!.startVideoRecording();
        print("New recording started successfully.");
      }
    } catch (e) {
      print("Error during recording process: $e");
    }
  }

  void _stopRecording() {
    if (!_isRecording) {
      print("Recording is already stopped.");
      return;
    }

    setState(() => _isRecording = false);
    print("Recording stopped by user.");

    if (_cameraController?.value.isRecordingVideo == true) {
      _cameraController?.stopVideoRecording();
      print("Recording stopped on camera.");
    }
  }

  @override
  void dispose() {
    _cameraService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Heart Rate Monitor')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (_cameraController != null && _cameraController!.value.isInitialized)
              ClipOval(child: CameraPreview(_cameraController!)),
            Text('Last BPM: ${_displayedHeartRate.toStringAsFixed(2)}'),
            ElevatedButton(
              onPressed: _isRecording
                  ? null
                  : () {
                      if (!_audioService.isPlaying) {
                        // Start playSoundInLoop only once
                        Future(() => _audioService.playSoundInLoop());
                      }
                      _startRecording(); // Start recording video
                    },
              child: Text('Start'),
            ),
            ElevatedButton(
              onPressed: _isRecording ? _stopRecording : null,
              child: Text('Stop'),
            ),
          ],
        ),
      ),
    );
  }
}
