import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'session_data_manager.dart'; // adjust import

class SessionDataPage extends StatefulWidget {
  const SessionDataPage({super.key});

  @override
  State<SessionDataPage> createState() => _SessionDataPageState();
}

class _SessionDataPageState extends State<SessionDataPage> {
  final manager = SessionDataManager();

  Future<void> _downloadData(String id) async {
    final dir = await getApplicationDocumentsDirectory();
    final name = manager.names[id] ?? "session_$id";
    final path = "${dir.path}/$name.json";
    final file = File(path);
    await file.writeAsString(jsonEncode(manager.sessionData[id]));
    await Share.shareXFiles(
      [XFile(file.path, mimeType: 'application/json')],
      text: 'Download of session "$name"',
    );
  }

  @override
  Widget build(BuildContext context) {
    final entries = manager.sessionData.entries.toList();

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text("Session Data"),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: ListView.builder(
        itemCount: entries.length,
        itemBuilder: (_, index) {
          final id = entries[index].key;
          final name = manager.names[id] ?? "Session $id";

          return ListTile(
            title: TextField(
              controller: TextEditingController(text: name),
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                labelText: "Session Name",
                labelStyle: TextStyle(color: Colors.grey),
              ),
              onChanged: (value) => manager.names[id] = value,
            ),
            trailing: IconButton(
              icon: const Icon(Icons.download, color: Colors.white),
              onPressed: () => _downloadData(id),
            ),
          );
        },
      ),
    );
  }
}
