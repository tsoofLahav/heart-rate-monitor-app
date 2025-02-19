import 'dart:async';
import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

class VideoService {
  static final VideoService _instance = VideoService._internal();
  factory VideoService() => _instance;
  VideoService._internal();

  late VideoPlayerController _videoController;
  bool _isInitialized = false;

  void initialize() {
    if (_isInitialized) return;
    _videoController = VideoPlayerController.asset("assets/video.mp4")
      ..initialize().then((_) {
        _videoController.setLooping(false);
        _videoController.play();
      });
    _isInitialized = true;
  }

  void updatePlaybackSpeed(double playTime) {
    if (playTime <= 0 && _isInitialized) return;
    double videoDuration = _videoController.value.duration.inSeconds.toDouble();
    double playbackSpeed = videoDuration / playTime;
    _videoController.setPlaybackSpeed(playbackSpeed);
    if (!_videoController.value.isPlaying) {
      _videoController.play();
    }
  }

  Widget getVideoWidget() {
    return _isInitialized && _videoController.value.isInitialized
        ? AspectRatio(
            aspectRatio: _videoController.value.aspectRatio,
            child: VideoPlayer(_videoController),
          )
        : Center(child: CircularProgressIndicator());
  }
}
