import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class BackendService {
  Future<Map<String, dynamic>?> sendVideoToBackend(File videoFile) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('https://heart-rate-monitor-app.onrender.com/process_video'),
      );
      request.files.add(await http.MultipartFile.fromPath('video', videoFile.path));

      var response = await request.send();

      if (response.statusCode == 200) {
        var responseBody = await response.stream.bytesToString();
        return jsonDecode(responseBody);
      }
    } catch (e) {
      return null;
    }
    return null;
  }
}
