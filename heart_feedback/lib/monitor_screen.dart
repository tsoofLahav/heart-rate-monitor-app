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
    _cameraController = await _cameraService.initializeCamera(cameras);
    setState(() {});
  }

  Future<void> _startRecording() async {
    setState(() => _isRecording = true);

    final directory = await getApplicationDocumentsDirectory();
    final videoPath = '${directory.path}/heart_rate_video.mp4';

    while (_isRecording) {
      await Future.delayed(Duration(seconds: 1));
      XFile videoFile = await _cameraController!.stopVideoRecording();
      await _cameraController!.startVideoRecording();
      File newFile = await File(videoFile.path).copy(videoPath);

      var result = await _backendService.sendVideoToBackend(newFile);
      if (result != null) {
        _audioService.processPeaks(result['peaks'], result['newStart']);
        setState(() {
          _displayedHeartRate = result['heart_rate'] ?? 0.0;
        });
      }
    }
  }

  void _stopRecording() {
    setState(() => _isRecording = false);
    _cameraController?.stopVideoRecording();
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
              onPressed: _isRecording ? null : _startRecording,
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
