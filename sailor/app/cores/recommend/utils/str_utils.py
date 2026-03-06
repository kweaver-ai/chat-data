# """
# @File: str_utils.py
# @Desc: 字符串处理函数
# """
#
# import re
#
#
# def is_all_chinese(ustring):
# 	"""判断字符串是否都是中文"""
# 	for uchar in ustring:
# 		if not is_chinese(uchar):
# 			return False
# 	return True
#
#
# def is_all_alphabet(ustring):
# 	"""判断字符串是否都是英文"""
# 	for uchar in ustring:
# 		if not is_alphabet(uchar):
# 			return False
# 	return True
#
#
# def is_all_number(ustring):
# 	"""判断字符串是否都是数字"""
# 	for uchar in ustring:
# 		if not is_number(uchar):
# 			return False
# 	return True
#
#
# def is_all_alphabet_and_number(ustring):
# 	"""判断字符串是否都是英文、数字"""
# 	for uchar in ustring:
# 		if not is_alphabet(uchar) and not is_number(uchar):
# 			return False
# 	return True
#
#
# def is_chinese(uchar):
# 	"""判断一个unicode是否是汉字"""
# 	if u'\u4e00' <= uchar <= u'\u9fa5':
# 		return True
# 	else:
# 		return False
#
#
# def is_number(uchar):
# 	"""判断一个unicode是否是数字"""
# 	if u'\u0030' <= uchar <= u'\u0039':
# 		return True
# 	else:
# 		return False
#
#
# def is_alphabet(uchar):
# 	"""判断一个unicode是否是英文字母"""
# 	if (u'\u0041' <= uchar <= u'\u005a') or (u'\u0061' <= uchar <= u'\u007a'):
# 		return True
# 	else:
# 		return False
#
#
# def is_other(uchar):
# 	"""判断是否非汉字，数字和英文字符"""
# 	if not (is_chinese(uchar) or is_number(uchar) or is_alphabet(uchar)):
# 		return True
# 	else:
# 		return False
#
#
# def B2Q(uchar):
# 	"""半角转全角"""
# 	# 不是半角字符就返回原来的字符
# 	inside_code = ord(uchar)
# 	if inside_code < 0x0020 or inside_code > 0x7e:
# 		return uchar
# 	# 除了空格其他的全角半角的公式为:半角=全角-0xfee0
# 	if inside_code == 0x0020:
# 		inside_code = 0x3000
# 	else:
# 		inside_code += 0xfee0
# 	return chr(inside_code)
#
#
# def Q2B(uchar):
# 	"""全角转半角"""
# 	inside_code = ord(uchar)
# 	if inside_code == 0x3000:
# 		inside_code = 0x0020
# 	else:
# 		inside_code -= 0xfee0
# 	# 转完之后不是半角字符返回原来的字符
# 	if inside_code < 0x0020 or inside_code > 0x7e:
# 		return uchar
# 	return chr(inside_code)
#
#
# def stringQ2B(ustring):
# 	"""把字符串全角转半角"""
# 	return ''.join([Q2B(uchar) for uchar in ustring])
#
#
# def uniform(ustring):
# 	"""格式化字符串，完成全角转半角，大写转小写的工作"""
# 	return stringQ2B(ustring).lower()
#
#
# def uniform_punctuation(ustring, stopwords=[]):
# 	"""删除文本中的标点符号"""
# 	# ptn_en = re.compile(r'[\`\~\!\@\#\$\%\^\&\*\(\)\_\+\-\=\[\]\{\}\\\|\;\'\'\:\"\"\,\.\/\<\>\?]')
# 	# ptn_zh = re.compile(r'[\·\~\！\@\#\￥\%\……\&\*\（\）\——\-\+\=\【\】\{\}\、\|\；\‘\’\：\“\”\《\》\？\，\。\、]')
# 	ptn_en = re.compile(r'[\`\~\!\@\#\$\%\^\&\*\_\+\-\=\[\]\{\}\\\|\;\'\'\:\"\"\,\.\/\<\>\?]')
# 	ptn_zh = re.compile(r'[\·\~\！\@\#\￥\%\……\&\*\——\-\+\=\【\】\{\}\、\|\；\‘\’\：\“\”\《\》\？\，\。\、]')
# 	ustring = re.sub(ptn_zh, '', ustring)
# 	ustring = re.sub(ptn_en, '', ustring)
# 	ustring = stringQ2B(ustring=ustring)
# 	for w in stopwords:
# 		ustring = ustring.replace(w, '')
# 	return ustring.lower()
#
#
# def string2List(ustring):
# 	"""将ustring按照中文，字母，数字分开"""
# 	retList = []
# 	utmp = []
# 	for uchar in ustring:
# 		if is_other(uchar):
# 			if len(utmp) == 0:
# 				continue
# 			else:
# 				retList.append(''.join(utmp))
# 				utmp = []
# 		else:
# 			utmp.append(uchar)
# 	if len(utmp) != 0:
# 		retList.append(''.join(utmp))
# 	return retList
#
#
# def varify_str(ustring, default_val=''):
# 	if ustring is None or str(ustring).lower() == 'null' or not ustring:
# 		return default_val
# 	return ustring
#
#
# if __name__ == '__main__':
# 	# text = 'aac009'
# 	# print(is_all_alphabet_and_number(text))
# 	# print(is_alphabet('a'))
# 	# print(is_chinese('你'))
# 	# print(ord('a'))
#
# 	line = '你好（人）'
# 	print(uniform_punctuation(ustring=line))
# 	pass
