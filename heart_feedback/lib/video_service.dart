import 'dart:async';
import 'dart:collection';
import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';
import 'monitor_screen.dart'; // Ensure HeartRateMonitor exists

class VideoService extends StatefulWidget {
  final bool notReading;
  final double averageGap;
  final List<double> intervals;
  final bool newStart;

  VideoService({
    required this.notReading,
    required this.averageGap,
    required this.intervals,
    required this.newStart,
  });

  @override
  _VideoServiceState createState() => _VideoServiceState();
}

class _VideoServiceState extends State<VideoService> {
  late VideoPlayerController _controller;
  final Queue<double> _timeQueue = Queue<double>();
  double _aveGap = 1.0;
  double _diff = 0.0;
  int _inputCount = 0;
  bool _isPlaying = false;

  @override
  void initState() {
    super.initState();
    _controller = VideoPlayerController.asset("assets/video.mp4")
      ..initialize().then((_) {
        _controller.play(); // Ensure the video starts immediately
        setState(() {});
      });

    _processData(widget.notReading, widget.averageGap, widget.intervals, widget.newStart);
  }

  /// **Handles queue management & playback logic**
  void _processData(bool notReading, double averageGap, List<double> intervals, bool newStart) {
    if (notReading) {
      _timeQueue.clear();
      _isPlaying = false;
      return;
    }

    if (averageGap != 1.0) {
      _diff = averageGap - _aveGap;
      _aveGap = averageGap;
    }

    if (newStart && _timeQueue.isNotEmpty) {
      double lastValue = _timeQueue.removeLast();
      _timeQueue.add(lastValue + intervals[0]); // Merge last with first interval
      _timeQueue.addAll(intervals.sublist(1));
    } else {
      _timeQueue.addAll(intervals);
    }

    _inputCount++;
    if (_inputCount > 1 && !_isPlaying) {
      _isPlaying = true;
      _playLoop();
    }
  }

  /// **Plays video at adjusted speed based on queue times**
  Future<void> _playLoop() async {
    while (_timeQueue.isNotEmpty) {
      double playTime = _timeQueue.removeFirst() + _diff;
      if (playTime <= 0) continue;

      double videoDuration = _controller.value.duration.inSeconds.toDouble();
      double playbackSpeed = videoDuration / playTime;

      _controller.setPlaybackSpeed(playbackSpeed);

      if (!_controller.value.isPlaying) {
        _controller.play(); // Ensures video continues playing smoothly
      }

      print("Playing at speed: $playbackSpeed");

      await Future.delayed(Duration(milliseconds: (playTime * 1000).toInt()));
    }
    _isPlaying = false;
  }

  /// **Stops video and returns to HeartRateMonitor**
  void _stopVideo() {
    _controller.pause();
    _timeQueue.clear();
    _isPlaying = false;
    Navigator.pushReplacement(
        context, MaterialPageRoute(builder: (context) => HeartRateMonitor(useAudioService: false)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _controller.value.isInitialized
              ? AspectRatio(
                  aspectRatio: _controller.value.aspectRatio,
                  child: VideoPlayer(_controller),
                )
              : CircularProgressIndicator(),
          SizedBox(height: 20),
          ElevatedButton(
            onPressed: _stopVideo,
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: Text("Stop", style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}
