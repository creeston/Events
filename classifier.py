from fastai.text import load_learner
from preprocess import TextPreprocessor
from models import Event

event_type_mapping = {
    "Выставка": "exhibition",
    "Встреча": "lecture",
    "Вечеринка": "party",
    "Дегустация": "food",
    "Занятие": "training",
    "Интенсив": "training",
    "Игра": "game",
    "Квест": "game",
    "Концерт": "concert",
    "Квиз": "game",
    "Конкурс": "compete",
    "Конференция": "festival",
    "Лекция": "lecture",
    "Мастер-класс": "training",
    "Модный показ": "show",
    "Просмотр": "view",
    "Презентация": "lecture",
    "Разговорный клуб": "training",
    "Семинар": "training",
    "Стендап": "standup",
    "Спектакль": "theater",
    "Спортивное мероприятие": "sport",
    "Тренинг": "training",
    "Турнир": "compete",
    "Фестиваль": "festival",
    "Хакатон": "compete",
    "Шоу": "show",
    "Экскурсия": "tour",
    "Ярмарка": "market"
}


event_types = [
    "compete",
    "concert",
    "concert_programm",
    "exhibition",
    "festival",
    "food",
    "free",
    "game",
    "lecture",
    "market",
    "online",
    "open air",
    "party",
    "show",
    "sport",
    "standup",
    "theatre",
    "tour",
    "training",
    "view"
]


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
