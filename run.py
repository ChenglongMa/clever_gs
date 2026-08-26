import os
import re
import sys
import time
import json
import ipdb
import random
import requests
import itertools
import traceback
import threading
import Levenshtein
from seleniumbase import Driver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime


def main(first_name, last_name, google_scholar_code, lookback="1"):
	# TODO - initials and name permutations
	AUTHOR_NAME = {
			"f_m" : [first_name],
			"l" : [last_name]
		}

	def req(url): return requests.get(url).content.decode("utf-8")

	def rgx(p, t): 
		try: return re.findall(p, t, re.MULTILINE | re.DOTALL)
		except: return list()

	def rgx_sub_a(p, t):
		try: return rgx(p, t)[0].split(" ")[-1]
		except: pass

	google_scholar_entries_path = os.path.join(os.getcwd(), "google_scholar_entries.json")
	google_scholar_entries = list()
	if (not os.path.exists(google_scholar_entries_path)):
		driver = Driver(uc=True, page_load_strategy="eager")
		driver.get(f"https://scholar.google.com/citations?user={google_scholar_code}&hl=en")
		page_html = driver.execute_script("return document.documentElement.outerHTML;")
		driver.execute_script(open("jquery").read())
		assert ("gsc_bpf_more" in page_html)
		while (not "disabled" in re.findall("(?<=\\<button type\\=\"button\" id\\=\"gsc_bpf_more\").*?(?=\\<)", page_html)[0]):
			driver.execute_script("$(\"#gsc_bpf_more\").click();")
			time.sleep(random.randint(2,5))
			page_html = driver.execute_script("return document.documentElement.outerHTML;")
			assert ("gsc_bpf_more" in page_html)
		driver.close()
		entries = re.findall(r'(?<=\<td class\=\"gsc_a_t\"\>).*?(?<=\<\/tr\>)', page_html)
		for x in entries:
			google_scholar_entries.append({
					"title" : re.findall(r'(?<=class\=\"gsc_a_at\"\>).*?(?=\<\/a\>)', x)[0],
					"date" : re.findall(r'(?<=gsc_a_h gsc_a_hc gs_ibl\"\>).*?(?=\<)', x)[0],
					"journal" : re.findall(r'(?<=\<\/div\>\<div class\=\"gs_gray\"\>).*?(?=\<)', x)[0],
					"authors" : re.findall(r'(?<=\<\/a\>\<div class\=\"gs\_gray\"\>).*?(?=\<)', x)[0]
				})
		with open(google_scholar_entries_path, "w") as f:
			f.write(json.dumps(google_scholar_entries,indent=3))
			f.close()
	else:
		google_scholar_entries = json.loads(open(google_scholar_entries_path).read())


	adms_entries_path = os.path.join(os.getcwd(), "adms_entries.json")
	adms_entries = list()
	if (not os.path.exists(adms_entries_path)):
		author_name_alts = list(); [[author_name_alts.append({"f_m":f_m, "l":l}) 
										for f_m in AUTHOR_NAME["f_m"]] for l in AUTHOR_NAME["l"]]
		ADMS_CENTRE_PUBLICATION_DIRECTORY = "https://www.admscentre.org.au/publications-library/"
		re_alts = [f"(?<=handleAuthorClick\\(this, ).*?(?=\\);'>{x['l']}\\, {x['f_m']})" for x in author_name_alts]
		# Get the author directory from the ADM+S site
		html_publication_dir = req(ADMS_CENTRE_PUBLICATION_DIRECTORY)
		author_codes = list(set([x for x in [rgx_sub_a(re_alt, html_publication_dir) for re_alt in re_alts] if (x is not None)]))
		adms_entries = list()
		for this_author_code in author_codes:
			html_for_ac = req(f"https://www.admscentre.org.au/publications-library/?auth={this_author_code}")
			for x in rgx(r'(?<=\<pre\>).*?(?=\<\/pre\>)', html_for_ac):
				try:
					adms_entries.append(re.findall(r"(?<=title = \{).*?(?=\})",re.sub('<[^<]+?>', str(), x))[0])
				except:
					pass
		adms_entries = list(set(adms_entries))
		with open(adms_entries_path, "w") as f:
			f.write(json.dumps(adms_entries,indent=3))
			f.close()
	else:
		adms_entries = json.loads(open(adms_entries_path).read())


	# Get Google Scholar profile entries

	def are_similar(x,y):
		return (Levenshtein.distance(x.lower(), y.lower()) <= 15)

	LOOKBEHIND = max(int(lookback), 1) if lookback.isdigit() else 1
	CURRENT_YEAR = datetime.now().year
	flagged_entries = list()
	years_qualifying = list(range(CURRENT_YEAR - LOOKBEHIND, CURRENT_YEAR + 1))
	for x in google_scholar_entries:
		try:
			if ((not any([are_similar(x["title"], y) for y in adms_entries])) and (int(x["date"]) in years_qualifying)):
				flagged_entries.append(x)
		except:
			pass

	print(json.dumps(flagged_entries, indent=3))

if (__name__ == "__main__"):
	first_name = sys.argv[1] # "Abdul"
	last_name = sys.argv[2] # "Obeid"
	google_scholar_code = sys.argv[3] # "iAtNdR8AAAAJ"
	lookback = sys.argv[4] if (len(sys.argv) > 4) else "1"
	main(first_name, last_name, google_scholar_code, lookback)
