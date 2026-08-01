import json

path = '/Users/ethanzhang/Documents/Personal/repositories/projects/maid2/glossary.json'

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

new_descriptions = {
    ("Daisy Fager", "Lu"): "Master (Lu) and servant (Daisy) in disguise, but in reality Lu is fiercely protective of Daisy and acts as her psychological 'exit' in illusions. They share a deep bond of trust.",
    ("Daisy Fager", "Head Maid"): "The Head Maid relies heavily on Daisy (disguised as Viscount Weatherwoods) to maintain the family's honor, creating a dynamic of mutual dependence and professional respect.",
    ("Daisy Fager", "Butler Assassin"): "A transactional alliance built on mutual benefit. They maintain a professional, somewhat tense working relationship.",
    ("Daisy Fager", "Raffaello"): "Former comrades in arms from a 10-year war. Raffaello respects 'Andert' immensely, but currently views Daisy with intense suspicion, unaware of her true identity.",
    ("Lu", "Head Maid"): "Strained and suspicious. The Head Maid is highly wary of Lu's overwhelming power and enigmatic nature, while Lu remains casually dismissive.",
    ("Daisy Fager", "Count Roseville"): "Former comrades and mentor-student dynamic. Roseville treats 'Gray' with a mix of respect and high expectations, unaware it is actually Daisy.",
    ("Viscount Gray Weatherwoods", "Yegashi", "Volkwin"): "An informal, friendly trio who have dropped formalities to speak comfortably, transcending their differences in social status.",
    ("Viscount Gray Weatherwoods", "Jin Berkleigh-Grayton"): "One-sided admiration. Jin idolizes Gray and desperately wishes to be his disciple, while Gray remains firm in rejecting her.",
    ("Viscount Gray Weatherwoods", "Jiharc Berkleigh-Grayton"): "A tense, silent battle of wits. Jiharc is highly suspicious of Gray's identity and constantly tests him, while Gray attempts to maintain his cover.",
    ("Jin Berkleigh-Grayton", "Auster"): "Hostile competitors engaged in a bitter rivalry over family succession.",
    ("Jiharc Berkleigh-Grayton", "Jin Berkleigh-Grayton"): "A strained father-daughter dynamic where Jiharc manipulates Jin as a figurehead for his covert operations.",
    ("Daisy Fager", "Jin Berkleigh-Grayton"): "A master-servant dynamic on paper, but characterized by Jin's intense idolization and stubborn intrusion into Daisy's life.",
    ("Daisy Fager", "Jiharc Berkleigh-Grayton"): "A highly cautious relationship filled with mutual suspicion and hidden agendas.",
    ("Yegashi", "Volkwin"): "Close friends and confidants who rely on each other to cope with intense family pressure. They share a deep, mutually supportive bond."
}

for rel in data.get('relationships', []):
    chars = tuple(rel.get('characters', []))
    if chars in new_descriptions:
        rel['description'] = new_descriptions[chars]

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Updated glossary.json successfully.")
