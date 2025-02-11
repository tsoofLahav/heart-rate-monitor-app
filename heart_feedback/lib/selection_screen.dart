import 'package:flutter/material.dart';
import 'monitor_screen.dart';

class SelectionScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              "Welcome to Heart Feedback App,\nchoose your feedback method",
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white, fontSize: 18),
            ),
            SizedBox(height: 30),
            ElevatedButton(
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => HeartRateMonitor(useAudioService: false),
                  ),
                );
              },
              style: ElevatedButton.styleFrom(backgroundColor: Colors.white),
              child: Text("Visual", style: TextStyle(color: Colors.black)),
            ),
            SizedBox(height: 10),
            ElevatedButton(
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => HeartRateMonitor(useAudioService: true),
                  ),
                );
              },
              style: ElevatedButton.styleFrom(backgroundColor: Colors.white),
              child: Text("Audio", style: TextStyle(color: Colors.black)),
            ),
          ],
        ),
      ),
    );
  }
}
