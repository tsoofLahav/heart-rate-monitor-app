import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class BackendService {
  Future<Map<String, dynamic>?> sendVideoToBackend(File videoFile) async {
    try {
      print("Sending video to backend: ${videoFile.path}");
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('https://heart-rate-monitor-app.onrender.com/process_video'),
      );
      request.files.add(await http.MultipartFile.fromPath('video', videoFile.path));

      var response = await request.send();
      print("Backend response status code: ${response.statusCode}");

      if (response.statusCode == 200) {
        var responseBody = await response.stream.bytesToString();
        print("Backend response body: $responseBody");
        return jsonDecode(responseBody);
      } else {
        print('Error response from backend: ${response.statusCode}');
      }
    } catch (e) {
      print('Exception when sending video to backend: $e');
    }
    return null;
  }
}
