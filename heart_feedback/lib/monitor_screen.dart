// Import necessary packages and services
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'camera_service.dart';
import 'backend_service.dart';
import 'audio_service.dart';
import 'dart:async';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

// Define the main stateful widget for heart rate monitoring
class HeartRateMonitor extends StatefulWidget {
  @override
  _HeartRateMonitorState createState() => _HeartRateMonitorState();
}

class _HeartRateMonitorState extends State<HeartRateMonitor> {
  // Initialize services for camera, backend processing, and audio feedback
  final CameraService _cameraService = CameraService();
  final BackendService _backendService = BackendService();
  final AudioService _audioService = AudioService();

  // Variables for camera control, heart rate display, status messages, and recording state
  CameraController? _cameraController;
  double _displayedHeartRate = 0.0;
  String _statusMessage = "";
  bool _isRecording = false;
  final List<File> _videoQueue = [];
  final Object _queueLock = Object();

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  // Initialize the camera
  Future<void> _initialize() async {
    WidgetsFlutterBinding.ensureInitialized();
    List<CameraDescription> cameras = await availableCameras();
    _cameraController = await _cameraService.initializeCamera(cameras);
    if (_cameraController?.value.isInitialized == true) {
      setState(() {});
    }
  }

  // Continuously records short video clips for heart rate analysis
  Future<void> _recordLoop() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;
    _isRecording = true;
    
    final directory = await getApplicationDocumentsDirectory();
    while (_isRecording) {
      final videoPath = '${directory.path}/heart_rate_video_${DateTime.now().millisecondsSinceEpoch}.mp4';
      await _cameraController!.startVideoRecording();
      await Future.delayed(Duration(seconds: 1));
      XFile videoFile = await _cameraController!.stopVideoRecording();
      
      _safeQueueUpdate(() {
        _videoQueue.add(File(videoFile.path).copySync(videoPath));
      });
    }
  }

  // Processes recorded videos by sending them to the backend for analysis
  Future<void> _processingLoop() async {
    while (_isRecording) {
      File? videoFile;
      
      _safeQueueUpdate(() {
        if (_videoQueue.isNotEmpty) {
          videoFile = _videoQueue.removeAt(0);
        }
      });
      
      if (videoFile != null) {
        var result = await _backendService.sendVideoToBackend(videoFile!);
        if (result != null) {
          _audioService.processData(result['not_reading'], result['ave_gap'], result['intervals_list'], result['new_start']);
          
          setState(() {
            if (result['not_reading']) {
              _statusMessage = "Unstable reading, place finger on camera";
            } else if (!_audioService.isPlaying) {
              _statusMessage = "Loading...";
            } else {
              if (result['bpm'] != -1) {
                _displayedHeartRate = result['bpm'];
              }
              _statusMessage = "BPM: ${_displayedHeartRate.toStringAsFixed(2)}";
            }
          });
        }
      } else {
        await Future.delayed(Duration(milliseconds: 100));
      }
    }
  }

  // Thread-safe method for updating the video queue
  void _safeQueueUpdate(void Function() action) {
    synchronized(_queueLock, action);
  }

  // Starts heart rate monitoring by initiating recording and processing loops
  void _startMonitoring() {
    if (_isRecording) return;
    _isRecording = true;
    _recordLoop();
    _processingLoop();
  }

  // Stops heart rate monitoring
  void _stopMonitoring() {
    if (!_isRecording) return;
    _isRecording = false;
  }

  @override
  void dispose() {
    _cameraService.dispose();
    super.dispose();
  }

  // UI layout for the heart rate monitor
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
            Text(_statusMessage, style: TextStyle(fontSize: 18)),
            ElevatedButton(
              onPressed: _isRecording ? null : _startMonitoring,
              child: Text('Start'),
            ),
            ElevatedButton(
              onPressed: _isRecording ? _stopMonitoring : null,
              child: Text('Stop'),
            ),
          ],
        ),
      ),
    );
  }
}

// Helper function for synchronizing queue updates
void synchronized(Object lock, void Function() action) {
  return action();
}
