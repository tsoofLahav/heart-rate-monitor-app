import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import '../camera_service.dart';
import 'monitoring_service.dart';

class HeartRateMonitor extends StatefulWidget {
  @override
  _HeartRateMonitorState createState() => _HeartRateMonitorState();
}

class _HeartRateMonitorState extends State<HeartRateMonitor> {
  final CameraService _cameraService = CameraService();
  final MonitoringService _monitoringService = MonitoringService();

  CameraController? _cameraController;
  String _statusMessage = "";

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    WidgetsFlutterBinding.ensureInitialized();
    List<CameraDescription> cameras = await availableCameras();
    _cameraController = await _cameraService.initializeCamera(cameras);
    if (_cameraController?.value.isInitialized == true) {
      setState(() {});
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
            Text(_monitoringService.statusMessage, style: TextStyle(fontSize: 18)),
            ElevatedButton(
              onPressed: _monitoringService.isRecording ? null : _monitoringService.startMonitoring,
              child: Text('Start'),
            ),
            ElevatedButton(
              onPressed: _monitoringService.isRecording ? _monitoringService.stopMonitoring : null,
              child: Text('Stop'),
            ),
          ],
        ),
      ),
    );
  }
}
