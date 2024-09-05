import os
import re
import chardet
from collections import defaultdict
from flask import Flask, request, render_template, redirect, url_for
from textblob import TextBlob
from newspaper import Article
from werkzeug.utils import secure_filename
from flask_executor import Executor

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['EXECUTOR_TYPE'] = 'thread'  # Use threads for asynchronous processing
app.config['EXECUTOR_MAX_WORKERS'] = 4  # Number of workers for processing
executor = Executor(app)

def process_text(file_path=None, url=None):
    text = ""
    if file_path:
        with open(file_path, 'rb') as file:  # Open the file in binary mode
            raw_data = file.read()  # Read the raw bytes
            result = chardet.detect(raw_data)  # Detect the encoding
            encoding = result['encoding']  # Get the detected encoding
            
            if encoding is None:  # Fallback to 'utf-8' if encoding detection fails
                encoding = 'utf-8'
                
        try:
            text = raw_data.decode(encoding)  # Decode the binary data using the detected/fallback encoding
        except (UnicodeDecodeError, LookupError):
            # If decoding fails, use a more lenient approach or another fallback
            text = raw_data.decode('utf-8', errors='replace')
    elif url:
        article = Article(url)
        article.download()
        article.parse()
        text = article.text

    # Tokenize and clean text
    words = re.findall(r'\b\w+\b', text.lower())

    # Count word frequency
    word_freq = defaultdict(int)
    for word in words:
        word_freq[word] += 1

    # Sort by frequency and get top 10 words
    top_words = sorted(word_freq.items(), key=lambda item: item[1], reverse=True)[:10]

    # Sentiment analysis
    blob = TextBlob(text)
    sentiment = blob.sentiment.polarity  # returns value between -1 and 1

    if sentiment > 0.2:
        sentiment_summary = "Positive"
    elif -0.2 <= sentiment <= 0.2:
        sentiment_summary = "Neutral"
    else:
        sentiment_summary = "Negative"

    return word_freq, top_words, sentiment_summary

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('file')
        url = request.form.get('url')
        file_path = None

        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

        word_freq, top_words, sentiment_summary = process_text(file_path=file_path, url=url)

        return render_template('results.html', word_freq=word_freq, top_words=top_words, sentiment_summary=sentiment_summary)

    return render_template('upload.html')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(host="127.0.0.1", port=8080, debug=True)
