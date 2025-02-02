import 'package:audioplayers/audioplayers.dart';
import 'dart:collection';
import 'dart:async';

class AudioService {
  final AudioPlayer _audioPlayer = AudioPlayer();
  final Queue<int> _intervalQueue = Queue<int>();
  bool _isPlaying = false;
  double _aveGap = 1.0; // Global average gap (seconds)
  int _delayTime = 0; // Global delay time (milliseconds)
  final _queueLock = Object(); // Lock object to ensure atomic updates

  bool get isPlaying => _isPlaying;

  Future<void> _playLoop() async {
    if (_isPlaying) return;
    _isPlaying = true;

    while (true) {
      int? waitTime;
      
      synchronized(_queueLock, () {
        if (_intervalQueue.isNotEmpty) {
          waitTime = _intervalQueue.removeFirst();
        } else {
          _isPlaying = false;
          return;
        }
      });
      
      if (waitTime != null) {
        await _audioPlayer.play(AssetSource('boom.mp3'));
        await Future.delayed(Duration(milliseconds: waitTime!));
      }
    }
  }

  void processData(bool unstableReading, double newAveGap, List<double> intervals, bool newStart) {
    if (unstableReading) {
      synchronized(_queueLock, () {
        _intervalQueue.clear();
        _isPlaying = false;
      });
      return;
    }

    synchronized(_queueLock, () {
      if (newAveGap != -1) {
        double gapDifference = (newAveGap - _aveGap) * 1000;
        _aveGap = newAveGap;
        List<int> tempList = _intervalQueue.toList();
        for (int i = 0; i < tempList.length; i++) {
          tempList[i] += gapDifference.toInt();
        }
        _intervalQueue
          ..clear()
          ..addAll(tempList);
      }
    });

    List<int> newIntervals = intervals.map((i) => (i * 1000).toInt()).toList();

    synchronized(_queueLock, () {
      if (newStart || _intervalQueue.isEmpty) {
        _intervalQueue.addAll(newIntervals);
        if (_intervalQueue.isNotEmpty) {
          int startDelay = ((_aveGap * 5 - (1 + _delayTime / 1000)) * 1000).toInt();
          Future.delayed(Duration(milliseconds: startDelay), _playLoop);
        }
      } else {
        int lastValue = _intervalQueue.isNotEmpty ? _intervalQueue.last : 0;
        _intervalQueue.addAll(newIntervals.map((interval) => lastValue + interval));
      }
    });

    if (!_isPlaying) _playLoop();
  }
}

void synchronized(Object lock, void Function() action) {
  // Ensures atomic execution of actions on shared resources
  return action();
}
