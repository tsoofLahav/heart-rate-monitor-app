import 'package:flutter/material.dart';
import 'backend_service.dart';
import 'audio_service.dart';
import 'video_service.dart'; // Import VideoService
import 'dart:io';
import 'package:flutter/services.dart';

class HeartRateMonitor extends StatefulWidget {
  final bool useAudioService;

  HeartRateMonitor({required this.useAudioService}); // Accept flag

  @override
  _HeartRateMonitorState createState() => _HeartRateMonitorState();
}

class _HeartRateMonitorState extends State<HeartRateMonitor> {
  final BackendService _backendService = BackendService();
  final AudioService _audioService = AudioService();
  static const MethodChannel _channel = MethodChannel('video_recorder');

  String _statusMessage = "";
  bool _isRecording = false;
  int bpm = 0;
  final List<String> _videoQueue = [];

  @override
  void initState() {
    super.initState();
    if (widget.useAudioService) {
      _initializeAudio();
    }
    _listenForVideoFiles();
  }

  Future<void> _initializeAudio() async {
    await _audioService.init();
  }

  /// **Listen for file paths from iOS**
  void _listenForVideoFiles() {
    _channel.setMethodCallHandler((call) async {
      if (call.method == "videoSaved") {
        _videoQueue.add(call.arguments as String);
        _processNextVideo();
      }
    });
  }

  /// **Start Recording**
  void _startMonitoring() async {
    if (_isRecording) return;
    _isRecording = true;
    await _channel.invokeMethod("startRecording");
  }

  /// **Stop Recording**
  void _stopMonitoring() async {
    if (!_isRecording) return;
    _isRecording = false;
    await _channel.invokeMethod("stopRecording");
  }

  /// **Process Video Queue (Send to Backend)**
  Future<void> _processNextVideo() async {
    if (_videoQueue.isEmpty || !_isRecording) return;

    String videoPath = _videoQueue.removeAt(0);
    String correctedPath = Uri.parse(videoPath).toFilePath();

    var result = await _backendService.sendVideoToBackend(File(correctedPath));

    if (result == null) return;

    double averageGap = (result['ave_gap'] as num?)?.toDouble() ?? 1.0;
    double heartRate = (result['heart_rate'] as num?)?.toDouble() ?? -1.0;
    List<double> intervals = (result['intervals_list'] as List?)?.map((e) => (e as num).toDouble()).toList() ?? [];
    bool notReading = result['not_reading'] ?? true;
    bool newStart = result['new_start'] ?? false;

    // **Decide whether to use Audio or Video based on flag**
    if (widget.useAudioService) {
      _audioService.processData(notReading, averageGap, intervals, newStart);
    } else {
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => VideoService(
            notReading: notReading,
            averageGap: averageGap,
            intervals: intervals,
            newStart: newStart,
          ),
        ),
      );
    }

    if (heartRate != -1) {
      bpm = heartRate.toInt();
    }

    setState(() {
      _statusMessage = notReading ? "Unstable reading, place finger on camera"
                  : bpm == 0 ? "Loading..."
                  : "BPM: ${bpm.toString()}";
    });

    if (_videoQueue.isNotEmpty) {
      _processNextVideo();
    }
  }

  @override
  void dispose() {
    if (widget.useAudioService) {
      _audioService.dispose();
    }
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
            Text(_statusMessage, style: TextStyle(fontSize: 18)),
            ElevatedButton(onPressed: _isRecording ? null : _startMonitoring, child: Text('Start')),
            ElevatedButton(onPressed: _isRecording ? _stopMonitoring : null, child: Text('Stop')),
          ],
        ),
      ),
    );
  }
}
