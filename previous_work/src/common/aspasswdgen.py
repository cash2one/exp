#!/usr/bin/python

import random

# Readable, easy input in mobile and web.
# Strong password
class ReadableRandomPassGen:
  def __init__(self):
    random.seed()
    self.__lower_chars = [
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n',
        'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
    self.__upper_chars = [
        'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N',
        'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
    # No 0, 1 because it's confusing
    self.__digits = [ '2', '3', '4', '5', '6', '7', '8', '9' ]
    # Common, easy to find.
    # In iphone, same page as digits.
    self.__symbols = [ '@', '/', ':', ';', '(', ')', '"', '.', ',', '?', '!']

  def Get(self):
    # 16 chars in 4 group.
    # One group include 1 Upper chars, and 3 lower chars
    # One group of pure lower chars
    # One group composed of digit and one symbol
    # One random group
    groups = []
    groups.append(self.__upper_group())
    groups.append(self.__lower_group())
    groups.append(self.__symbol_group())
    groups.append(self.__rand_group())
    random.shuffle(groups)
    return "".join(groups)

  def __upper_group(self):
    chars = []
    chars.append(self.__rand_upper_char())
    for i in range(3):
      chars.append(self.__rand_lower_char())
    random.shuffle(chars)
    return "".join(chars)

  def __lower_group(self):
    chars = []
    for i in range(4):
      chars.append(self.__rand_lower_char())
    return "".join(chars)

  def __symbol_group(self):
    chars = []
    for i in range(3):
      chars.append(self.__rand_digit())
    chars.append(self.__rand_symbol())
    random.shuffle(chars)
    return "".join(chars)

  def __rand_group(self):
    rand_idx = random.randint(0, 2)
    if rand_idx == 0:
      return self.__upper_group()
    elif rand_idx == 1:
      return self.__lower_group()
    else:
      return self.__symbol_group()


  def __rand_lower_char(self):
    num = random.randint(0, len(self.__lower_chars) - 1)
    return self.__lower_chars[num]

  def __rand_upper_char(self):
    num = random.randint(0, len(self.__upper_chars) - 1)
    return self.__upper_chars[num]

  def __rand_digit(self):
    num = random.randint(0, len(self.__digits) - 1)
    return self.__digits[num]

  def __rand_symbol(self):
    num = random.randint(0, len(self.__symbols) - 1)
    return self.__symbols[num]

if __name__ == '__main__':
	pass_gen = ReadableRandomPassGen()
	for i in range(5):
		print pass_gen.Get()
