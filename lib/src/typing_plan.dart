import 'dart:math';

const _neighbors = <String, String>{
  'a': 'qwsz',
  'b': 'vghn',
  'c': 'xdfv',
  'd': 'serfcx',
  'e': 'wsdr',
  'f': 'drtgvc',
  'g': 'ftyhbv',
  'h': 'gyujnb',
  'i': 'ujko',
  'j': 'huikmn',
  'k': 'jiolm',
  'l': 'kop',
  'm': 'njk',
  'n': 'bhjm',
  'o': 'iklp',
  'p': 'ol',
  'q': 'wa',
  'r': 'edft',
  's': 'awedxz',
  't': 'rfgy',
  'u': 'yhji',
  'v': 'cfgb',
  'w': 'qase',
  'x': 'zsdc',
  'y': 'tghu',
  'z': 'asx',
  '1': '2q',
  '2': '13qw',
  '3': '24we',
  '4': '35er',
  '5': '46rt',
  '6': '57ty',
  '7': '68yu',
  '8': '79ui',
  '9': '80io',
  '0': '9op',
};

const _alphabet = 'abcdefghijklmnopqrstuvwxyz';

String readUnit(String source, int index) {
  if (index < 0 || index >= source.length) return '';
  if (index + 1 < source.length) {
    final pair = source.substring(index, index + 2);
    if (pair == '\r\n' || pair == '\n\r') return pair;
    final unit = source.codeUnitAt(index);
    final next = source.codeUnitAt(index + 1);
    if (unit >= 0xD800 &&
        unit <= 0xDBFF &&
        next >= 0xDC00 &&
        next <= 0xDFFF) {
      return pair;
    }
  }
  return source[index];
}

bool isNewline(String unit) =>
    unit == '\n' || unit == '\r' || unit == '\r\n' || unit == '\n\r';

bool shouldMistake(Random random, int perHundred, String unit) {
  if (perHundred <= 0 || unit.length != 1 || unit.trim().isEmpty) {
    return false;
  }
  return random.nextInt(100) < perHundred.clamp(0, 100);
}

int sampleMistakeLength(Random random, int average) {
  final avg = average.clamp(1, 20);
  if (avg == 1) return 1;
  switch (random.nextInt(4)) {
    case 0:
      return avg - 1;
    case 3:
      return avg + 1;
    default:
      return avg;
  }
}

String wrongCharacter(Random random, String unit) {
  if (unit.isEmpty) return 'a';
  final original = unit[0];
  final lower = original.toLowerCase();
  final neighbors = _neighbors[lower];
  var pick = (neighbors != null && neighbors.isNotEmpty)
      ? neighbors[random.nextInt(neighbors.length)]
      : _alphabet[random.nextInt(_alphabet.length)];
  if (pick == lower && RegExp(r'[a-z]').hasMatch(lower)) {
    pick = _alphabet[(lower.codeUnitAt(0) - 97 + 1) % 26];
  }
  if (original != lower) return pick.toUpperCase();
  return pick;
}
