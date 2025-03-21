import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Make sure we have the necessary NLTK data
nltk.download('punkt')
nltk.download('stopwords')

# Test word tokenization
text = "Hello there! This is a test of NLTK. Are you working properly? I hope so."
words = word_tokenize(text)
print("Tokenized words:")
print(words)

# Test stopword removal
stop_words = set(stopwords.words('english'))
filtered_words = [word for word in words if word.lower() not in stop_words]
print("\nAfter removing stopwords:")
print(filtered_words)

print("\nNLTK is working correctly!") 