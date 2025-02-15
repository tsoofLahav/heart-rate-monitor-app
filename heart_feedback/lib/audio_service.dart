import 'dart:async';
import 'dart:collection';
import 'package:flutter_soloud/flutter_soloud.dart';
import 'package:path_provider/path_provider.dart';
import 'package:flutter/services.dart'; // For rootBundle
import 'dart:io';

class AudioService {
  final SoLoud _soloud = SoLoud.instance;
  AudioSource? _source;
  final Queue<double> _waitQueue = Queue<double>();
  bool _isPlaying = false;
  double _oldAveGap = 1.0;
  double _newAveGap = 1.0;
  double _gapDiff = 0.0;
  late String _soundFilePath; // Store path for reuse

  /// **Initialize SoLoud and load audio**
  Future<void> init() async {
    print("[AudioService] Initializing SoLoud...");

    if (!SoLoud.instance.isInitialized) {
      try {
        await SoLoud.instance.init();
        print("[AudioService] SoLoud initialized successfully.");
      } catch (e) {
        print("[AudioService] ERROR: Failed to initialize SoLoud - $e");
        return;
      }
    }

    try {
      // Check if the asset exists
      await rootBundle.load('assets/boom.wav');
      print("[AudioService] Asset found in bundle.");

      // Copy asset to application documents directory and get its path
      _soundFilePath = await _copyAssetToAppDocs('assets/boom.wav');

      // Load sound from file instead of asset
      _source = await _soloud.loadFile('assets/boom.wav');
      if (_source == null) {
        print("[AudioService] ERROR: Failed to load sound file.");
      } else {
        print("[AudioService] Sound file loaded successfully from app documents storage.");
      }
    } catch (e) {
      print("[AudioService] ERROR: Exception while loading sound - $e");
    }
  }

  /// **Copy asset file to application documents directory and return its path**
  Future<String> _copyAssetToAppDocs(String assetPath) async {
    final appDocsDir = await getApplicationDocumentsDirectory();
    final appDocsPath = '${appDocsDir.path}/boom.wav';
    final file = File(appDocsPath);

    if (!await file.exists()) {
      final byteData = await rootBundle.load(assetPath);
      await file.writeAsBytes(byteData.buffer.asUint8List(), flush: true);
      print("[AudioService] Copied asset to $appDocsPath.");
    }

    return appDocsPath;
  }

  /// **Process incoming heart rate data and schedule playback**
  void processData(bool notReading, double averageGap, List<double> intervals, bool newStart) {
    if (_source == null) {
      print("[AudioService] WARNING: Audio source is null. Cannot play.");
      return;
    }

    if (notReading) {
      _waitQueue.clear();
      _isPlaying = false;
      return;
    }

    if (averageGap != 1.0) {
      _oldAveGap = _newAveGap;
      _newAveGap = averageGap;
      _gapDiff = (_newAveGap - _oldAveGap);
    }

    if (newStart && _waitQueue.isNotEmpty) {
      double lastValue = _waitQueue.removeLast();
      _waitQueue.add(lastValue + intervals[0]);
      _waitQueue.addAll(intervals.sublist(1));
    } else {
      _waitQueue.addAll(intervals);
    }

    if (!_isPlaying) {
      _isPlaying = true;
      _playLoop().then((_) => _isPlaying = false);
    }
  }

  /// **Audio playback loop**
  Future<void> _playLoop() async {
    if (_source == null) {
      print("[AudioService] ERROR: Cannot play, source is null.");
      return;
    }

    while (_waitQueue.isNotEmpty) {
      SoundHandle handle = await _soloud.play(_source!, volume: 1.0);
      print("[AudioService] Playing sound, handle: ${handle.id}");

      if (handle.id == 0) {
        print("[AudioService] ERROR: SoLoud failed to play sound.");
        return;
      }


      double waitTime = _waitQueue.removeFirst() + _gapDiff;
      await Future.delayed(Duration(milliseconds: (waitTime * 1000).toInt()));
    }
  }

  /// **Dispose SoLoud and stop playing sounds**
  Future<void> dispose() async {
    if (_source != null) {
      await _soloud.disposeSource(_source!);
      _source = null;
    }
    SoLoud.instance.deinit;
  }
}
