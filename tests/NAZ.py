import numpy as np
import json

# Serialize data into file:
QUESTIONS = json.load( open( "/home/nic/al/commissaire/tests/QUESTIONS.json" ) )

punteggio = 0
Ntot      = len(QUESTIONS.items())

for question, alternatives in QUESTIONS.items():
    correct_answer = alternatives[0]
    print(f"\n##############################a#################### \n\n{question}? \n")
    choice = np.array(["a", "b", "c", "d"])
    for i, alternative in enumerate(sorted(alternatives)):
        print(f"{choice[i]}) {alternative}")
    answer = input("\n> ")

    ind = np.isin(np.array(sorted(alternatives)), correct_answer)
    if answer == choice[ind][0]:
        print("Correct!")
        punteggio += 1
    else:
        print(f"The answer is {correct_answer!r}, not {choice[ind][0]!r}")

print("\n\nPunteggio finale: {:.2f} %".format(punteggio/Ntot*100))










"""

CLASS GEN

if CronoIND: np.sum(frazioni)
sum(piazzamenti) for p in tappa
piazzamento ultima tappa


CLASS SQ GIORNO

if CronoSQ: reg. spec.
else: sum(top 3 tempi) 
sum(piazzamenti primi 3 tempi) in tappa
piazzamento migliore ultima tappa

CLASS SQ GEN

sum(3 migliori tempi individuali)
sum(piazzamenti sq. giorno) 
migliore in generale individuale












"""