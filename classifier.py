from fastai.text import load_learner
from preprocess import TextPreprocessor
from models import Event, event_types


class TypeClassifier:
    torch_labels = sorted([str(i) for i in range(20)])

    def __init__(self, model_path):
        self.model = load_learner(model_path)
        self.preprocessor = TextPreprocessor()

    def predict_event_type(self, event: Event):
        text = event.to_str()
        return self.predict_type(text)

    def predict_type(self, text):
        text = self.preprocessor.preprocess_text(text)
        p = self.model.predict(text)
        result = []
        for index, i in enumerate(p[1]):
            if int(i) == 1:
                true_label = int(self.torch_labels[index])
                result.append(event_types[true_label])
        return result
