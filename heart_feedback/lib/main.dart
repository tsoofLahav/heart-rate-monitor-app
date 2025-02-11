import 'package:flutter/material.dart';
import 'selection_screen.dart'; // Import SelectionScreen

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: SelectionScreen(), // Redirect to selection screen first
    );
  }
}
