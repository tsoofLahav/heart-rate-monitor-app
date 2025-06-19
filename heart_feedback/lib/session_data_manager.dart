import 'package:uuid/uuid.dart';

class SessionDataManager {
  static final SessionDataManager _instance = SessionDataManager._internal();
  factory SessionDataManager() => _instance;
  SessionDataManager._internal();

  final List<double> _audioStartTimes = [];
  final Map<String, Map<String, dynamic>> _sessionData = {};
  final Map<String, String> _names = {};

  void addAudioStartSignal({required bool valid}) {
    final now = DateTime.now().millisecondsSinceEpoch / 1000.0;
    _audioStartTimes.add(valid ? now : -1);
  }

  void saveSessionData(Map<String, dynamic> backendData) {
    final id = const Uuid().v4();
    _sessionData[id] = {
      "backend": backendData,
      "audioStartTimes": List.of(_audioStartTimes),
    };
    _audioStartTimes.clear();
  }

  void reset() {
    _audioStartTimes.clear();
  }

  Map<String, Map<String, dynamic>> get sessionData => _sessionData;
  Map<String, String> get names => _names;
}
