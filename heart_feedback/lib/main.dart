import 'package:flutter/material.dart';
import 'welcome.dart'; // Import CameraPage

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: WelcomePage(), // Redirect directly to CameraPage
    );
  }
}
