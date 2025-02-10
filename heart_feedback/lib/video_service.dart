import 'dart:async';
import 'package:flutter/services.dart';

class VideoService {
  static const MethodChannel _channel = MethodChannel('video_recorder');
  static const EventChannel _eventChannel = EventChannel('video_recorder_events');

  Stream<String>? _filePathStream;

  /// Starts continuous recording using iOS's AVFoundation
  Future<void> startRecording() async {
    await _channel.invokeMethod('startRecording');
  }

  /// Stream that listens for file paths sent from iOS for each video slice
  Stream<String> get filePathStream {
    _filePathStream ??= _eventChannel.receiveBroadcastStream().map((event) => event as String);
    return _filePathStream!;
  }
}
