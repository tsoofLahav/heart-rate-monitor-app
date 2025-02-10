import 'package:flutter/material.dart';
import 'backend_service.dart';
import 'audio_service.dart';
import 'dart:async';
import 'dart:io';
import 'package:camera/camera.dart';
import 'package:path_provider/path_provider.dart';

class HeartRateMonitor extends StatefulWidget {
  @override
  _HeartRateMonitorState createState() => _HeartRateMonitorState();
}

class _HeartRateMonitorState extends State<HeartRateMonitor> {
  final BackendService _backendService = BackendService();
  final AudioService _audioService = AudioService();

  double _displayedHeartRate = 0.0;
  String _statusMessage = "";
  bool _isRecording = false;
  final List<String> _videoQueue = [];
  final Object _queueLock = Object();

  CameraController? _cameraController;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  /// **Initialize the Camera with Flash**
  Future<void> _initializeCamera() async {
    final cameras = await availableCameras();
    if (cameras.isNotEmpty) {
      _cameraController = CameraController(cameras[0], ResolutionPreset.low);
      await _cameraController!.initialize();
      await _cameraController!.setFlashMode(FlashMode.torch); // Enable Flash
      setState(() {});
    } else {
      print("No camera available.");
    }
  }

  /// **Start Monitoring (Continuous Recording & Processing)**
  void _startMonitoring() async {
    if (_isRecording || _cameraController == null) return;
    _isRecording = true;

    _recordLoop(); // Start continuous recording
    _processingLoop(); // Start processing loop
  }

  /// **Stop Monitoring**
  void _stopMonitoring() {
    if (!_isRecording) return;
    _isRecording = false;

    // Stop recording if running
    _cameraController?.stopVideoRecording();
  }

  /// **Continuous Recording Without Stopping**
  Future<void> _recordLoop() async {
    if (_cameraController == null) return;

    while (_isRecording) {
      final directory = await getTemporaryDirectory();
      final filePath = '${directory.path}/video_${DateTime.now().millisecondsSinceEpoch}.mp4';

      try {
        await _cameraController!.startVideoRecording();
        await Future.delayed(Duration(seconds: 1)); // Capture 1-second slices
        final videoFile = await _cameraController!.stopVideoRecording();

        _safeQueueUpdate(() {
          _videoQueue.add(videoFile.path);
        });

        print("Video added to queue: ${videoFile.path}");
      } catch (e) {
        print("Recording error: $e");
      }
    }
  }

  /// **Process Recorded Videos (Send to Backend)**
  Future<void> _processingLoop() async {
    while (_isRecording) {
      String? videoPath;

      _safeQueueUpdate(() {
        if (_videoQueue.isNotEmpty) {
          videoPath = _videoQueue.removeAt(0);
        }
      });

      if (videoPath != null) {
        print("File size: ${File(videoPath as String).lengthSync()} bytes");
        var result = await _backendService.sendVideoToBackend(File(videoPath as String));
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
        await Future.delayed(Duration(milliseconds: 500)); // Avoid unnecessary looping
      }
    }
  }

  /// **Thread-Safe Video Queue Update**
  void _safeQueueUpdate(void Function() action) {
    synchronized(_queueLock, action);
  }

  @override
  void dispose() {
    _cameraController?.dispose();
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

// **Helper function for synchronizing queue updates**
void synchronized(Object lock, void Function() action) {
  return action();
}
