// Myers-Briggs personality types with descriptions and celebrity examples
window.mbtiTypes = {
  "INTJ": {
    "name": "INTJ - The Architect",
    "description": "INTJs are analytical problem-solvers, eager to improve systems and processes with their innovative ideas. They have a talent for seeing possibilities for improvement, whether at work, at home, or in themselves. Often intellectual, they value logic, knowledge, and competence.",
    "celebrities": "Female: Jane Austen, Hillary Clinton, Michelle Obama | Male: Elon Musk, Stephen Hawking, Mark Zuckerberg",
    "traits": "Strategic, independent, innovative, logical, reserved, insightful"
  },
  "INTP": {
    "name": "INTP - The Logician",
    "description": "INTPs are philosophical innovators, fascinated by logical analysis, systems, and design. They value knowledge, seeking patterns and connections that reveal underlying principles. INTPs are deeply theoretical, focusing on possibilities beyond the present.",
    "celebrities": "Female: Marie Curie, Emma Watson, Clara Bow | Male: Albert Einstein, Socrates, Bill Gates",
    "traits": "Analytical, objective, conceptual, curious, adaptable, theoretical"
  },
  "ENTJ": {
    "name": "ENTJ - The Commander",
    "description": "ENTJs are strategic leaders, motivated by challenge and the desire to lead organizations toward logical, efficient results. They're quick to see opportunities for improvement and eager to implement ideas that create systemic, long-term solutions.",
    "celebrities": "Female: Margaret Thatcher, Whoopi Goldberg, Charlize Theron | Male: Steve Jobs, Franklin D. Roosevelt, Gordon Ramsay",
    "traits": "Determined, strategic, commanding, efficient, driven, ambitious"
  },
  "ENTP": {
    "name": "ENTP - The Debater",
    "description": "ENTPs are inspired innovators, motivated by new ideas and championing improvement. Quick, clever, and curious, they create solutions to complex problems by connecting seemingly unrelated ideas. They're excited by challenges and thrive on debate.",
    "celebrities": "Female: Amy Poehler, Celine Dion, Gillian Anderson | Male: Leonardo da Vinci, Thomas Edison, Hugh Laurie",
    "traits": "Inventive, debating, adaptable, resourceful, outspoken, original"
  },
  "INFJ": {
    "name": "INFJ - The Advocate",
    "description": "INFJs are creative nurturers with a strong sense of personal integrity and a drive to help others realize their potential. Complex and deeply intuitive, they have an uncanny insight into people and situations. INFJs care deeply about causes and people.",
    "celebrities": "Female: Nicole Kidman, Oprah Winfrey, Lady Gaga | Male: Martin Luther King Jr., Nelson Mandela, Morgan Freeman",
    "traits": "Insightful, compassionate, principled, complex, determined, idealistic"
  },
  "INFP": {
    "name": "INFP - The Mediator",
    "description": "INFPs are imaginative idealists, guided by their own core values and beliefs. To a Mediator, possibilities are paramount; the reality of the moment is only of passing concern. They see potential for a better future and pursue truth and meaning in their own unique way.",
    "celebrities": "Female: Audrey Hepburn, Winona Ryder, Julia Roberts | Male: William Shakespeare, J.R.R. Tolkien, Johnny Depp",
    "traits": "Idealistic, empathetic, creative, authentic, curious, compassionate"
  },
  "ENFJ": {
    "name": "ENFJ - The Protagonist",
    "description": "ENFJs are charismatic and inspiring leaders, able to mesmerize their listeners. They are usually idealistic, with high values and a natural confidence that attracts others. They're at their best while helping others achieve personal growth.",
    "celebrities": "Female: Oprah Winfrey, Maya Angelou, Jennifer Lawrence | Male: Barack Obama, Dr. Martin Luther King Jr., John Cusack",
    "traits": "Charismatic, inspiring, empathetic, loyal, persuasive, supportive"
  },
  "ENFP": {
    "name": "ENFP - The Campaigner",
    "description": "ENFPs are people-centered creators with a focus on possibilities and a contagious enthusiasm for new ideas, people and activities. Energetic, warm, and passionate, ENFPs love to help others explore their creative potential.",
    "celebrities": "Female: Ellen DeGeneres, Sandra Bullock, Jennifer Aniston | Male: Robin Williams, Robert Downey Jr., Mark Twain",
    "traits": "Enthusiastic, creative, sociable, free-spirited, energetic, optimistic"
  },
  "ISTJ": {
    "name": "ISTJ - The Logistician",
    "description": "ISTJs are responsible organizers, driven to create and enforce order within systems and institutions. They are neat and orderly, inside and out, with a place for everything and everything in its place. They're methodical and reliable, systematically working through projects from beginning to end.",
    "celebrities": "Female: Queen Elizabeth II, Condoleezza Rice, Angela Merkel | Male: Denzel Washington, Sean Connery, Tom Hanks",
    "traits": "Practical, dependable, organized, loyal, logical, methodical"
  },
  "ISFJ": {
    "name": "ISFJ - The Defender",
    "description": "ISFJs are industrious caretakers, loyal to traditions and organizations. They are practical, compassionate, and caring, and are motivated to provide for others and protect them from life's dangers. Practical and down-to-earth, they quietly work behind the scenes to make sure everyone's basic needs are met.",
    "celebrities": "Female: Kate Middleton, Queen Elizabeth II, Mother Teresa | Male: Vin Diesel, Elijah Wood, Bob Ross",
    "traits": "Supportive, reliable, observant, patient, devoted, protective"
  },
  "ESTJ": {
    "name": "ESTJ - The Executive",
    "description": "ESTJs are hardworking traditionalists, eager to take charge in organizing projects and people. Orderly, rule-abiding, and conscientious, they like to get things done and tend to go about projects in a systematic, methodical way. They're practical, conventional, and fact-minded.",
    "celebrities": "Female: Judge Judy, Michelle Obama, Sonia Sotomayor | Male: John D. Rockefeller, Frank Sinatra, Billy Graham",
    "traits": "Organized, logical, assertive, leadership-oriented, direct, dedicated"
  },
  "ESFJ": {
    "name": "ESFJ - The Consul",
    "description": "ESFJs are conscientious helpers, sensitive to the needs of others and energetically dedicated to their responsibilities. They are community-minded, with well-developed emotional intelligence. Popular and sympathetic, they tend to put the needs of others above their own.",
    "celebrities": "Female: Taylor Swift, Jennifer Garner, Selena Gomez | Male: Hugh Jackman, Chris Evans, Steve Harvey",
    "traits": "Caring, social, loyal, harmonious, practical, responsible"
  },
  "ISTP": {
    "name": "ISTP - The Virtuoso",
    "description": "ISTPs are observant artisans with an understanding of mechanics and an interest in troubleshooting. They approach their environments with quiet reserve and a sense of unpredictability. Ready to deviate from the rules they feel are irrelevant, they're tactical problem-solvers and hands-on workers.",
    "celebrities": "Female: Scarlett Johansson, Milla Jovovich, Ellen Page | Male: Clint Eastwood, Tom Cruise, Bruce Lee",
    "traits": "Adaptable, practical, logical, analytical, spontaneous, independent"
  },
  "ISFP": {
    "name": "ISFP - The Adventurer",
    "description": "ISFPs are gentle caretakers who live in the present moment and enjoy their surroundings with cheerful, low-key enthusiasm. They are flexible and spontaneous, and like to go with the flow to enjoy what life has to offer. ISFPs are quiet and unassuming, and may be hard to get to know.",
    "celebrities": "Female: Britney Spears, Marilyn Monroe, Frida Kahlo | Male: Michael Jackson, Bob Dylan, David Beckham",
    "traits": "Sensitive, artistic, gentle, harmonious, spontaneous, loyal"
  },
  "ESTP": {
    "name": "ESTP - The Entrepreneur",
    "description": "ESTPs are energetic thrillseekers who are at their best when putting out fires, whether literal or metaphorical. They bring a sense of dynamic energy to their interactions with others and the world around them. They assess situations quickly and move adeptly to respond to immediate problems.",
    "celebrities": "Female: Madonna, Miley Cyrus, Angelina Jolie | Male: Donald Trump, Bruce Willis, Eddie Murphy",
    "traits": "Bold, practical, observant, direct, rational, spontaneous"
  },
  "ESFP": {
    "name": "ESFP - The Entertainer",
    "description": "ESFPs are vivacious entertainers who charm and engage those around them. They are spontaneous, energetic, and fun-loving, and take pleasure in the things around them: food, clothes, nature, animals, and especially people. They are typically at the center of attention and take delight in the spotlight.",
    "celebrities": "Female: Adele, Kylie Jenner, Paris Hilton | Male: Jamie Foxx, Will Smith, Leonardo DiCaprio",
    "traits": "Enthusiastic, fun-loving, sociable, spontaneous, charismatic, practical"
  }
};

// Function to handle MBTI selection
window.handleMbtiSelection = function(mbtiType) {
  const descriptionElement = document.getElementById('mbtiDescription');
  const celebritiesElement = document.getElementById('mbtiCelebrities');
  
  if (mbtiType && window.mbtiTypes && window.mbtiTypes[mbtiType]) {
    const mbtiInfo = window.mbtiTypes[mbtiType];
    descriptionElement.textContent = mbtiInfo.description || 'No description available';
    
    if (mbtiInfo.celebrities) {
      celebritiesElement.textContent = 'Famous examples: ' + mbtiInfo.celebrities;
    } else {
      celebritiesElement.textContent = '';
    }
  } else {
    descriptionElement.textContent = 'Select an MBTI type to view the description.';
    celebritiesElement.textContent = '';
  }
};