import 'dart:async';
import 'dart:collection';
import 'dart:isolate';

class ProcessingService {
  static final ProcessingService _instance = ProcessingService._internal();
  factory ProcessingService() => _instance;
  ProcessingService._internal();

  final Queue<double> _timeQueue = Queue<double>();
  double _aveGap = 1.0;
  double _diff = 0.0;
  ReceivePort? _receivePort;

  void startProcessingIsolate() {
    _receivePort = ReceivePort();
    Isolate.spawn(_processLoop, _receivePort!.sendPort);
  }

  static void _processLoop(SendPort sendPort) async {
    while (true) {
      await Future.delayed(Duration(milliseconds: 100));
      sendPort.send(true); // Notify that processing is running
    }
  }

  /// **Process new heart rate data (Updates the queue)**
  void processData(bool notReading, double averageGap, List<double> intervals, bool newStart) {
    if (notReading) {
      _timeQueue.clear();
      return;
    }

    if (averageGap != 1.0) {
      _diff = averageGap - _aveGap;
      _aveGap = averageGap;
    }

    if (newStart && _timeQueue.isNotEmpty) {
      double lastValue = _timeQueue.removeLast();
      _timeQueue.add(lastValue + intervals[0]);
      _timeQueue.addAll(intervals.sublist(1));
    } else {
      _timeQueue.addAll(intervals);
    }

    print("Queue updated: $_timeQueue");
  }

  /// **Get the next interval time (Removes from queue)**
  Future<double> getNextInterval() async {
    while (_timeQueue.isEmpty) {
      await Future.delayed(Duration(milliseconds: 100));
    }
    return _timeQueue.removeFirst();
  }
}
