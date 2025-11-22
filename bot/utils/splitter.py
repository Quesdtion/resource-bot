# utils/splitter.py

MAX_TG_MESSAGE_LEN = 4000  # запас перед лимитом 4096


def split_message_lines(lines, max_len: int = MAX_TG_MESSAGE_LEN):
    """
    Разбивает длинный список строк на несколько сообщений.
    """
    chunk = []
    cur_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 за перенос строки

        if cur_len + line_len > max_len and chunk:
            yield "\n".join(chunk)
            chunk = [line]
            cur_len = line_len
        else:
            chunk.append(line)
            cur_len += line_len

    if chunk:
        yield "\n".join(chunk)
