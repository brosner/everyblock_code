import re

def wikify(text):
    text = re.sub(r'\[(https?://.*?)\s+(.*?)\]', r'<a href="\1">\2</a>', text)
    text = re.sub(r'\[(\w{1,30})\s+(.*?)\]', r'<a href="/\1/">\2</a>', text)
    text = re.sub(r'\r?\n', '<br />', text)
    text = re.sub(r'(?m)^h(\d)\. (.*?)$', r'<h\1>\2</h\1>', text)
    return text
