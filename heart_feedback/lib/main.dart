import 'package:flutter/material.dart';
import 'selection_screen.dart'; // Import CameraPage

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: SelectionScreen(), // Redirect directly to CameraPage
    );
  }
}
