# backend/test_pipeline.py
# -*- coding: utf-8 -*-

# from dotenv import load_dotenv; load_dotenv()
from quiz.backend.gurukula_quizgen import run_single_quiz_pipeline, process_chapter_to_sheet_gdoc
from quiz.backend.config import app_config

# Load environment variables and app config
INPUT_SPREADSHEET_NAME = app_config["spreadsheets"]["input_name"]
OUTPUT_SPREADSHEET_NAME = app_config["spreadsheets"]["output_name"]


# --- Assume these are loaded from your env_config ---
# For testing, you might hardcode the path temporarily if env_config is an issue

# # Input
# chapter_text = """
#    Chapter 16

# By then, Kaṃsa summoned Pūtanā - the Rākṣhasī (राक्षसी) and asked her to scoot neighboring villages for a newborn male child. Through the powers of her Māyā (माया), Pūtanā transformed herself into a beautiful woman and began wandering the villages and cities that surrounded Mathurā and eventually reached Gokula. There, she saw a house from which several women were coming out. It was Nanda’s house and the village women had just been there to see the beautiful Kṛiṣhṇa. Pūtanā walked inside when no one was around. Kṛiṣhṇa was alone. She lifted him from the cradle, sat down and placed him on her lap. Pūtanā took the child and pressed his lips against her breasts filled with poisoned milk. Just a sip would have killed the child - any ordinary child. But this child was Bhagavān. Kṛiṣhṇa sucked on Pūtanā’s breasts with such vigor that she felt her very life being sucked out of her. She began to scream. She shirked. But to no avail. Pūtanā let out such a deafening cry of agony that everyone heard it like thunder. And she fell down lifeless. Pūtanā instantly changed into her original Rākṣhasī form. People rushed to the spot and were amazed at seeing an enormous Rākṣhasī dead. And little Kṛiṣhṇa sitting on her body and playing. Yaśhodā rushed and picked Kṛiṣhṇa up. She held him close in her arms and hurried away from the presence of the dead Rākṣhasī.

# The Gopas (गोप) of Gokula dragged Pūtanā’s body with great difficulty and burnt it. From the fire emerged an amazing glow. And from her dead body came the fragrant smell of sandalwood and divine scents. Everyone was amazed.

# Pūtanā, by feeding the Supreme Bhagavān, had attained Mokṣha (मोक्ष). If a Rākṣhasī with the intent of destroying Bhagavān could attain Mokṣha because she fed Bhagavān with poison, imagine the fortune of Yaśhodā and the Gopīs (गोपी) who fed him with milk and dairy everyday.

# It is said that anyone who listens to this story, called Pūtanāmokṣha (पूतनामोक्ष), with attention and reverence, will forever be blessed with his mind eternally set on Kṛiṣhṇa. He will be blessed with unwavering devotion to Kṛiṣhṇa.

# Kṛiṣhṇa was now three months old and had learnt to turn over on his belly. One day, a large group of people from Gokula went to the banks of River Yamunā. Yaśhodā placed Kṛiṣhṇa in a cradle and placed the cradle under the cart in which they had travelled to protect him from the scorching sun.

# Kaṃsa’s henchman - Śhakaṭāsura (शकटासुर), had come there to kill Kṛiṣhṇa. Śhakaṭā had entered the wheel of the very cart under which Kṛiṣhṇa was placed. His plan was to kill Kṛiṣhṇa when no one was looking.

# Kṛiṣhṇa by this time had woken up. He crawled closer to the wheel of the cart and gave it a mighty kick with his legs that were as slender as a creeper. The entire cart was dislodged by the power of the kick. It flew and fell a great distance away, as though it was flung. It had turned upside down, with the metal jars containing milk and curd that was placed in the cart crushed. The cart’s pole was shattered. People wondered how the cart could dislodge itself in such a fashion. Some of the boys playing there said that they saw Kṛiṣhṇa kicking the cart. But no one believed that a three month old child was capable of kicking a cart, let alone cause such damage.

# In reality, it was Śhakaṭāsura that was the recipient of the kick and he immediately died. 

# History of Śhakaṭāsura

# Hiraṇyākṣha- who was killed by Bhagavān Viṣhṇu’s Varāha Avatāra, had a strong and powerful son called Utkacha (उत्कच). At one time, when this Rākṣhasa  destroyed the trees of Sage Lomaśha’s (लोमश) Āśhrama , the sage cursed that the Rākṣhasa  would lose his body. Utkacha asked for forgiveness and Sage Lomaśha said that the Rākṣhasa  would be liberated from the curse when Kṛiṣhṇa touched him with his feet. It was Utkacha who had entered the cart in his disembodied state and was subsequently liberated when Kṛiṣhṇa kicked him.

# Kṛiṣhṇa was now one year old. One day, Yaśhodā placed a sleeping Kṛiṣhṇa in the courtyard and went inside to do some household work. Just then, another henchman of Kaṃsa named Tṛṇāvarta (तृणावर्त) took the form of a whirlwind and came to Gokula. Everyone in Gokula was suddenly overpowered. A tornado seemed to have hit. The dust blew high. No one could see anything. Everyone held on to something and closed their eyes. It was noisy. Deafening.

# While everyone was distracted by the whirlwind, Tṛṇāvarta had carried Kṛiṣhṇa high into the sky with the objective of dashing him to the ground and killing him. The child, however, was becoming heavier and heavier for Tṛṇāvarta to carry. He tried to drop him, but Kṛiṣhṇa caught Asura's neck and squeezed it. Tṛṇāvarta was choking. He could not breathe. He struggled. He gasped. Tiny as the child’s hands were, they did not budge from Tṛṇāvarta’s neck. And he fell hard onto the ground. Dead.

# The whirlwind stopped. Everyone rushed to the dead Asura and found little Kṛiṣhṇa hanging onto his chest. They took the child and handed him to Yaśhodā. No one in Gokula knew how the Asura landed there. Or how he died. But they were delighted that their beloved child was safe. Little did they know that it was Kṛiṣhṇa who had brought an end to yet another Asura.
#  """

# # final_prompt = build_prompt(chapter_text, count=15, question_type="MCQ")

# # english_quiz_agent = build_english_quiz_agent("llama3-70b-8192")

# # # Get the response
# # response = english_quiz_agent.run(final_prompt)

# # parser = QuizParser()

# # english_quiz_text = parser.run(response.content if response.content is not None else "")
# # pprint(english_quiz_text)

# print("Generate Quiz")

# print(generate_quiz_json(chapter_text))

# print("Generated the Quiz")

print("Starting test pipeline...")

# run_single_quiz_pipeline("chapter33", input_source="file")

# Example Google Doc link (replace with a real one for actual test)
doc_link = "https://docs.google.com/document/d/1YyDyBCD-Wy4G6Kr_8PTBCxeMeJI6xjaUHGSca2xWVhQ/edit?usp=sharing"
num_questions = 5

spreadsheet_id = process_chapter_to_sheet_gdoc(doc_link, num_questions)
assert spreadsheet_id is not None
print(f"Tested Google Doc pipeline, spreadsheet id: {spreadsheet_id}")

print("Test pipeline executed successfully")
