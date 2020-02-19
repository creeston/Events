from interpreters import DateInterpreter

result = DateInterpreter.parse_relax_date("вт, 19 января 2038")
assert result[0] == 19 and result[1] == 1