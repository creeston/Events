from collections import Counter
import numpy as np
from sklearn import svm
import matplotlib.pyplot as plt

events = list(set(open('events', encoding="utf-8").readlines()))
not_events = list(set(open('not_events', encoding="utf-8").readlines()))

event_lengths = [len(e.split(' ')) for e in events]
plt.hist(event_lengths, bins=20)
plt.show()
not_event_lengths = [len(e.split(' ')) for e in not_events]
plt.hist(not_event_lengths, bins=20)
plt.show()

stop_words = {"и", "-", ".", "не", "+", ")", "(", "—", "–", ",", "|", "или", "\\", "/", ":"}


vocab = []
for event in events:
    event = event.strip()
    words = [w for w in event.split(' ') if w not in stop_words]

    word_counts = Counter(words)
    vocab.append(word_counts)

vocab = sum(vocab, Counter())
most_common = vocab.most_common(3000)
print(most_common)

vocab = dict()
words = ["UKN"]
for i, (k, v) in enumerate(most_common):
    vocab[k] = i + 1
    words.append(k)

vocab["UKN"] = 0


def text_to_vec(text):
    vec = np.zeros(len(words))
    for word in text.split(' '):
        if word in vocab:
            vec[vocab[word]] = 1
        else:
            vec[0] = 1
    return vec


events = [text_to_vec(event) for event in events]
test_events = events[201:]
train_events = events[:201]
not_events = [text_to_vec(not_event) for not_event in not_events]
train_not_events = not_events[:150]
test_not_events = not_events[150:]


y_train_events = np.zeros(len(train_events))
y_test_events = np.zeros(len(test_events))
y_test_events.fill(1)
y_train_events.fill(1)
y_train_not_events = np.zeros(len(train_not_events))
y_test_not_events = np.zeros(len(test_not_events))

x_train = np.concatenate((train_events, train_not_events))
y_train = np.concatenate((y_train_events, y_train_not_events))

x_test = np.concatenate((test_events, test_not_events))
y_test = np.concatenate((y_test_events, y_test_not_events))

for c in [1, 5, 10, 15, 20, 25, 35, 40, 45, 50, 55]:
    clf = svm.SVC(C=c)
    clf.fit(x_train, y_train)

    print("Training Accuracy:", (clf.score(x_train, y_train)) * 100, "%")
    print("For c=", c, " Testing Accuracy:", (clf.score(x_test, y_test)) * 100, "%")


