import 'dart:async';
import 'dart:isolate';
import 'dart:collection';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'backend_service.dart';
import 'audio_service.dart';
import 'video_service.dart';

class HeartRateMonitor extends StatefulWidget {
  final bool useAudioService;
  HeartRateMonitor({required this.useAudioService});
  @override
  _HeartRateMonitorState createState() => _HeartRateMonitorState();
}

class _HeartRateMonitorState extends State<HeartRateMonitor> {
  static const MethodChannel _channel = MethodChannel('video_recorder');
  bool _isRecording = false;
  String bpmMessage = "loading";
  late ReceivePort _receivePort;
  Isolate? _processingIsolate;
  SendPort? _sendPort;

  @override
  void initState() {
    super.initState();
    if (widget.useAudioService) {
      AudioService().init();
    }
    _startProcessingIsolate();
    _startBackgroundRecording();
  }

  /// **Starts the processing isolate for handling data**
  void _startProcessingIsolate() async {
    _receivePort = ReceivePort();
    _processingIsolate = await Isolate.spawn(_processingLoop, _receivePort.sendPort);

    _receivePort.listen((message) {
      if (message is SendPort) {
        _sendPort = message;
      } else if (message is String) {
        setState(() {
          bpmMessage = message;
        });
      } else if (message is double) {
        VideoService().updatePlaybackSpeed(message);
      }
    });
  }

  /// **Starts video recording on iOS background**
  void _startBackgroundRecording() async {
    if (!_isRecording) {
      _isRecording = true;
      await _channel.invokeMethod("startRecording");
      print("[HeartRateMonitor] Started background recording.");
    }
  }

  /// **Stops video recording**
  void _stopMonitoring() async {
    if (_isRecording) {
      _isRecording = false;
      await _channel.invokeMethod("stopRecording");
      print("[HeartRateMonitor] Stopped background recording.");
    }
  }

  @override
  void dispose() {
    _processingIsolate?.kill(priority: Isolate.immediate);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text("BPM: $bpmMessage", style: TextStyle(fontSize: 18, color: Colors.white)),
            SizedBox(height: 20),
            widget.useAudioService ? Container() : VideoService().getVideoWidget(),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: _isRecording ? null : _startBackgroundRecording,
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

/// **Processing Isolate: Handles Video Processing and Backend Communication**
void _processingLoop(SendPort mainSendPort) {
  final ReceivePort isolateReceivePort = ReceivePort();
  mainSendPort.send(isolateReceivePort.sendPort);
  final BackendService backendService = BackendService();
  final Queue<double> timeQueue = Queue<double>();
  double aveGap = 1.0;
  double diff = 0.0;

  isolateReceivePort.listen((message) async {
    if (message is String) {
      await _processVideo(File(message), backendService, mainSendPort, timeQueue, aveGap, diff);
    }
  });

  /// **Loop to send queue data at correct intervals**
  Future.delayed(Duration(seconds: 5), () async {
    while (true) {
      if (timeQueue.isEmpty) {
        await Future.delayed(Duration(milliseconds: 100));
        continue;
      }
      
      double playTime = timeQueue.removeFirst();
      mainSendPort.send(playTime);
      await Future.delayed(Duration(milliseconds: (playTime * 1000).toInt()));
    }
  });
}

/// **Processes video and updates the queue for playback**
Future<void> _processVideo(File videoFile, BackendService backendService, SendPort mainSendPort, Queue<double> timeQueue, double aveGap, double diff) async {
  var result = await backendService.sendVideoToBackend(videoFile);
  if (result == null) return;

  double newAveGap = (result['ave_gap'] as num?)?.toDouble() ?? 1.0;
  double heartRate = (result['heart_rate'] as num?)?.toDouble() ?? -1.0;
  List<double> intervals = (result['intervals_list'] as List?)?.map((e) => (e as num).toDouble()).toList() ?? [];
  bool notReading = result['not_reading'] ?? true;
  bool newStart = result['new_start'] ?? false;

  if (!notReading) {
    if (newAveGap != 1.0) {
      diff = newAveGap - aveGap;
      aveGap = newAveGap;
    }
    intervals = intervals.map((interval) => interval + diff).toList();
    
    if (newStart && timeQueue.isNotEmpty) {
      double lastValue = timeQueue.removeLast();
      timeQueue.add(lastValue + intervals[0] - diff);
      timeQueue.addAll(intervals.sublist(1));
    } else {
      timeQueue.addAll(intervals);
    }
  } else {
    timeQueue.clear();
  }

  String bpmMessage = notReading ? "not reading" : heartRate == -1 ? "loading" : heartRate.toInt().toString();
  mainSendPort.send(bpmMessage);
}
