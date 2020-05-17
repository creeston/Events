from markup import PlaceMarkup, MarkupCurrency

place_markup = PlaceMarkup()

text = "Группа 'Paradise Lost' (Великобритания). 8 февраля суббота. 19:00. Re:Public. г. Минск, ул. Притыцкого, 62."
places = place_markup.markup(text)
places = list(set([text[start:end] for _, start, end in places]))
assert places == ['Re:Public']


text = "Встреча на тему \"Если ваш близкий психически болен\" 6 марта с 16:30 до 18:00 Клубный дом \"Открытая душа\"."
places = place_markup.markup(text)
places = list(set([text[start:end] for _, start, end in places]))
assert places == ['Клубный дом \"Открытая душа\"']

text = "23 декабря 20:00 Культ.центр Корпус (Машерова 9)"
places = place_markup.markup(text)
places = list(set([text[start:end] for _, start, end in places]))
assert places == ['Культ.центр Корпус']

text = "Лекция «Маркетинг в жизни» 3 марта в 18:30 ул. Ленинградская, 20 (ФМО БГУ), ауд. 1201"
places = place_markup.markup(text)
places = list(set([text[start:end] for _, start, end in places]))
assert places == ['ФМО БГУ']

currency_markup = MarkupCurrency()

result = currency_markup.markup("Вход 8 - 12 рублей!")
assert result == [("MONEY", 5, 15)]

result = currency_markup.markup("Пишите в лс, на вайбер и звоните: +375291719148 (Viber) velcom, +375292627765 мтс.")
assert result == []

result = currency_markup.parse_currency("8 - 12 руб")
assert result == [8, 12]

result = currency_markup.parse_currency("12.50 рублей")
assert result == 12.5
