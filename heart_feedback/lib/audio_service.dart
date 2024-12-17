import 'package:audioplayers/audioplayers.dart';
import 'dart:collection';
import 'dart:async';

class AudioService {
  final AudioPlayer _audioPlayer = AudioPlayer();
  final Queue<int> _peakQueue = Queue<int>();

  Future<void> playSoundInLoop() async {
    while (true) {
      if (_peakQueue.isNotEmpty) {
        int waitTime = _peakQueue.removeFirst();
        await _audioPlayer.play(AssetSource('boom.mp3'));
        await Future.delayed(Duration(milliseconds: waitTime));
      } else {
        await Future.delayed(Duration(milliseconds: 100));
      }
    }
  }

  void processPeaks(List<dynamic> peaks, bool newStart) {
    for (var peak in peaks) {
      int peakMilliseconds = (peak == -1) ? 1000 : (peak * 1000).toInt();
      if (newStart || _peakQueue.isEmpty) {
        _peakQueue.add(peakMilliseconds);
      } else {
        _peakQueue.add(_peakQueue.last + peakMilliseconds);
      }
    }
  }
}
