#!/usr/bin/python3

from random import choice

gman = """Time, Dr. Freeman? 
Is it really that time again? 
It seems as if you only just arrived. You've done a great deal in a small time-span. 
You've done so well, in fact, that I've received some interesting offers for your services. 
Ordinarily I wouldn't contemplate them, but these are extra-ordinary times, hm? 
Rather than offer you the illusion of free choice, I will take the liberty of choosing for you... 
if, and when, your time comes round again. 
I do apologize for what must seem to you an arbitrary imposition, Dr. Freeman. 
I trust it will all make sense to you in the course of... well, I'm really not at liberty to say. 
In the meantime, this is where I get off. - G-Man, Half-Life 2"""

ryan = """I am Andrew Ryan, and I'm here to ask you a question. 
Is a man not entitled to the sweat of his brow? 'No!' says the man in Washington, 'It belongs to the poor.'
'No!' says the man in the Vatican, 'It belongs to God.' 
'No!' says the man in Moscow, 'It belongs to everyone.' 
I rejected those answers; instead, I chose something different. I chose the impossible. 
I chose... Rapture. 
A city where the artist would not fear the censor, 
where the scientist would not be bound by petty morality, 
where the great would not be constrained by the small! 
And with the sweat of your brow, Rapture can become your city as well. - Andrew Ryan, Bioshock
"""

locust = """Many of us are by the fire forsaken.
I speak of thine kind, and mine.
Behold this city! We are kindred, belike two eyes which gaze upon the other.
One poor girl slew her own kin, but even so, was embraced, enveloped by the Abyss.
Twas a comfort that neither moon nor sunless sky afforded her before.
And so, she lived in fear. Of the dark, of the things that gnawed at her flesh.
And yet! The Abyss hath yet to produce any such creature!
Fear not, the dark, my friend.
And let the feast begin. - Locust Preacher, Dark Souls 3"""

jabber = """Twas brillig, and the slithy toves did gyre and gimble in the wabe:
All mimsy were the borogroves, and the mome raths outgrabe.
Beware the Jabberwock my son! The jaws that bites, the claws that catch!
Beware the Jubjub bird, and shun the frumious Bandersnatch!
He took his vorpal sword in hand; Long time the manxome foe he sought-
So rested he by the Tumtum tree And stood awhile in thought. 
And, as in uffish thought he stood, the Jabberwock, with eyes of flame,
Came whiffling through the tulgey wood and burbled as it came!
One, two! One, two! And through and through The vorpal blade went snicker-snack!
He left it dead, and with its head He went galumphing back. - Lewis Caroll, Jabberwocky"""

gael = """What?
Still here?
Hand it over, that thing...
Your dark souls...
For my lady's painting...
Aah...
Is this the blood?
The blood fo the dark soul?
- Gael,
Dark Souls 3"""

open("input.txt", "w").write(choice([gman, ryan, locust, jabber, gael]))