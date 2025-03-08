
// Define MBTI types with detailed descriptions
const mbtiTypes = {
  "INTJ": {
    "name": "The Architect",
    "acronym": "Introverted, Intuitive, Thinking, Judging",
    "description": "INTJs are analytical problem-solvers, eager to improve systems and processes with their innovative ideas. They have a talent for seeing possibilities for improvement, whether at work, at home, or in themselves. Often intellectual, INTJs enjoy logical reasoning and complex problem-solving.",
    "celebrities": "Elon Musk, Mark Zuckerberg, Christopher Nolan, Jay-Z",
    "female_examples": "Nicole Kidman, Jodie Foster, Jane Austen, Michelle Obama",
    "male_examples": "Elon Musk, Mark Zuckerberg"
  },
  "INTP": {
    "name": "The Logician",
    "acronym": "Introverted, Intuitive, Thinking, Perceiving",
    "description": "INTPs are innovative inventors with an unquenchable thirst for knowledge. They are known for their brilliant theories and unrelenting logic. They love patterns and have an eye for spotting logical discrepancies. They often lose themselves in thought, which can make them appear detached or aloof.",
    "celebrities": "Albert Einstein, Bill Gates, Isaac Newton, Marie Curie",
    "female_examples": "Marie Curie, Tina Fey, Gillian Anderson, Emma Watson",
    "male_examples": "Albert Einstein, Bill Gates"
  },
  "ENTJ": {
    "name": "The Commander",
    "acronym": "Extraverted, Intuitive, Thinking, Judging",
    "description": "ENTJs are bold, imaginative, and strong-willed leaders, always finding a way or making one. They are natural-born leaders who embody charisma and confidence, projecting authority in a way that draws crowds together. However, they can be intimidating and overly dominant.",
    "celebrities": "Steve Jobs, Margaret Thatcher, Gordon Ramsay, Jim Carrey",
    "female_examples": "Margaret Thatcher, Charlize Theron, Oprah Winfrey, Taylor Swift",
    "male_examples": "Steve Jobs, Gordon Ramsay"
  },
  "ENTP": {
    "name": "The Debater",
    "acronym": "Extraverted, Intuitive, Thinking, Perceiving",
    "description": "ENTPs are smart and curious thinkers who cannot resist an intellectual challenge. They are often described as quick-witted, enthusiastic, outspoken, and sometimes even rebellious. They value knowledge and spend much of their time seeking a greater understanding of the world.",
    "celebrities": "Robert Downey Jr., Leonardo da Vinci, Thomas Edison, Richard Feynman",
    "female_examples": "Elizabeth Olsen, Amy Poehler, Julia Child, Salma Hayek",
    "male_examples": "Robert Downey Jr., Leonardo DiCaprio"
  },
  "INFJ": {
    "name": "The Advocate",
    "acronym": "Introverted, Intuitive, Feeling, Judging",
    "description": "INFJs are quiet, mystical, and intuitive idealists. They have an uncanny ability to understand people's true feelings and motivations. They are often seen as quiet and reserved but have rich, complex inner lives, with a strong moral compass and desire to help others achieve their potential.",
    "celebrities": "Martin Luther King Jr., Nelson Mandela, Carl Jung, Plato",
    "female_examples": "Nicole Kidman, Cate Blanchett, Daisy Ridley, Carrie Fisher",
    "male_examples": "Martin Luther King Jr., Benedict Cumberbatch"
  },
  "INFP": {
    "name": "The Mediator",
    "acronym": "Introverted, Intuitive, Feeling, Perceiving",
    "description": "INFPs are poetic, kind, and altruistic people, always looking to help a good cause. They see the world as a place of ideals and possibilities. They tend to be compassionate, understanding, and accepting, guided by their strong values and desire to contribute to humanity's well-being.",
    "celebrities": "William Shakespeare, Princess Diana, J.R.R. Tolkien, Johnny Depp",
    "female_examples": "Audrey Hepburn, Emma Watson, Alicia Keys, Björk",
    "male_examples": "Johnny Depp, J.R.R. Tolkien"
  },
  "ENFJ": {
    "name": "The Protagonist",
    "acronym": "Extraverted, Intuitive, Feeling, Judging",
    "description": "ENFJs are charismatic and inspiring leaders, able to mesmerize their listeners. They are often seen as warm and engaging, with a genuine passion to help others grow and develop. They are natural mentors who find joy in guiding others to their potential.",
    "celebrities": "Barack Obama, Oprah Winfrey, Nelson Mandela, Malala Yousafzai",
    "female_examples": "Jennifer Lawrence, Kate Winslet, Charlize Theron, Emma Stone",
    "male_examples": "Barack Obama, John Cusack"
  },
  "ENFP": {
    "name": "The Campaigner",
    "acronym": "Extraverted, Intuitive, Feeling, Perceiving",
    "description": "ENFPs are enthusiastic, creative, and sociable free spirits, who can always find a reason to smile. They tend to see life as a big, complex puzzle where everything is connected. They excel at understanding how people and the world works, and they're rarely satisfied with simplistic or standard solutions.",
    "celebrities": "Robin Williams, Walt Disney, Mark Twain, Robert Downey Jr.",
    "female_examples": "Jennifer Aniston, Sandra Bullock, Kelly Clarkson, Zooey Deschanel",
    "male_examples": "Robin Williams, Robert Downey Jr."
  },
  "ISTJ": {
    "name": "The Logistician",
    "acronym": "Introverted, Sensing, Thinking, Judging",
    "description": "ISTJs are practical and fact-minded individuals, whose reliability cannot be doubted. They value tradition, security, and peaceful living. They keep their spaces well-organized and take a methodical approach to their work. They tend to be reserved but will open up and relax with people they know well.",
    "celebrities": "Warren Buffett, George Washington, Jeff Bezos, Queen Elizabeth II",
    "female_examples": "Natalie Portman, Kate Middleton, Queen Elizabeth II, Michelle Obama",
    "male_examples": "Warren Buffett, Jeff Bezos"
  },
  "ISFJ": {
    "name": "The Defender",
    "acronym": "Introverted, Sensing, Feeling, Judging",
    "description": "ISFJs are very dedicated, warm protectors, always ready to defend their loved ones. They are often described as quiet, serious, and detail-oriented. They protect those they care about with devoted care and meticulous execution of their duties.",
    "celebrities": "Mother Teresa, Queen Elizabeth II, Dr. Fauci, Rosa Parks",
    "female_examples": "Kate Middleton, Anne Hathaway, Jessica Alba, Taylor Swift",
    "male_examples": "Vin Diesel, Jackie Chan"
  },
  "ESTJ": {
    "name": "The Executive",
    "acronym": "Extraverted, Sensing, Thinking, Judging",
    "description": "ESTJs are excellent administrators, unsurpassed at managing things or people. They value tradition and order, applying systematic approaches to their endeavors. They are practical, matter-of-fact individuals who enjoy bringing structure to their surroundings.",
    "celebrities": "Judge Judy, Lyndon B. Johnson, Mike Pence, Sonia Sotomayor",
    "female_examples": "Judge Judy, Sonia Sotomayor, Emma Roberts, Lucy Liu",
    "male_examples": "Frank Sinatra, Billy Graham"
  },
  "ESFJ": {
    "name": "The Consul",
    "acronym": "Extraverted, Sensing, Feeling, Judging",
    "description": "ESFJs are extraordinarily caring, social, and popular people, always eager to help. They are social creatures, seeking close relationships and supporting those they care about. They tend to take on the role of caretaker, ensuring the people in their lives are well looked after.",
    "celebrities": "Taylor Swift, Jennifer Garner, Hugh Jackman, Bill Clinton",
    "female_examples": "Jennifer Garner, Jennifer Lopez, Selena Gomez, Beyoncé",
    "male_examples": "Hugh Jackman, Chris Evans"
  },
  "ISTP": {
    "name": "The Virtuoso",
    "acronym": "Introverted, Sensing, Thinking, Perceiving",
    "description": "ISTPs are bold, practical experimenters, masters of all kinds of tools. They tend to be quiet and reserved, preferring to focus their energy on active problem-solving rather than abstract theories. They excel at understanding how mechanical things work and are typically reserved but curious observers.",
    "celebrities": "Tom Cruise, Clint Eastwood, Michael Jordan, Bear Grylls",
    "female_examples": "Scarlett Johansson, Kristen Stewart, Milla Jovovich, Angelina Jolie",
    "male_examples": "Tom Cruise, Bruce Lee"
  },
  "ISFP": {
    "name": "The Adventurer",
    "acronym": "Introverted, Sensing, Feeling, Perceiving",
    "description": "ISFPs are flexible, charming artists, always ready to explore and experience something new. They are quiet and reserved but also spontaneous and enthusiastic. They are deeply in touch with their senses and aesthetics, often having an artistic flair and appreciation for beauty.",
    "celebrities": "Bob Dylan, Britney Spears, Lana Del Rey, Michael Jackson",
    "female_examples": "Britney Spears, Lana Del Rey, Rihanna, Nicole Scherzinger",
    "male_examples": "Bob Dylan, Michael Jackson"
  },
  "ESTP": {
    "name": "The Entrepreneur",
    "acronym": "Extraverted, Sensing, Thinking, Perceiving",
    "description": "ESTPs are smart, energetic, and very perceptive people, who truly enjoy living on the edge. They are bold, rational, and empirical in their approach to life. They enjoy situations requiring quick action and practical solutions. They tend to be assertive, direct, and spontaneous risk-takers.",
    "celebrities": "Madonna, Jack Nicholson, Donald Trump, Eddie Murphy",
    "female_examples": "Madonna, Megan Fox, Miley Cyrus, Margot Robbie",
    "male_examples": "Jack Nicholson, Donald Trump"
  },
  "ESFP": {
    "name": "The Entertainer",
    "acronym": "Extraverted, Sensing, Feeling, Perceiving",
    "description": "ESFPs are spontaneous, energetic, and enthusiastic. They love life, new experiences, and meeting new people. They're often the life of the party, drawing others to them with their warmth and excitement. They live in the moment and enjoy making themselves and others happy through witty and entertaining conversation.",
    "celebrities": "Marilyn Monroe, Elvis Presley, Adele, Jamie Foxx",
    "female_examples": "Marilyn Monroe, Adele, Pink, Katy Perry",
    "male_examples": "Elvis Presley, Jamie Foxx"
  }
};

function handleMbtiSelection(mbtiType) {
  const descriptionElement = document.getElementById('mbtiDescription');
  const celebritiesElement = document.getElementById('mbtiCelebrities');
  const acronymElement = document.getElementById('mbtiAcronym');
  const femaleExamplesElement = document.getElementById('femaleCelebrities');
  const maleExamplesElement = document.getElementById('maleCelebrities');
  
  if (mbtiType && mbtiTypes && mbtiTypes[mbtiType]) {
    const mbtiInfo = mbtiTypes[mbtiType];
    descriptionElement.textContent = mbtiInfo.description || 'No description available';
    
    if (mbtiInfo.acronym) {
      acronymElement.textContent = 'Stands for: ' + mbtiInfo.acronym;
    } else {
      acronymElement.textContent = '';
    }
    
    if (mbtiInfo.celebrities) {
      celebritiesElement.textContent = 'Famous examples: ' + mbtiInfo.celebrities;
    } else {
      celebritiesElement.textContent = '';
    }
    
    if (mbtiInfo.female_examples) {
      femaleExamplesElement.textContent = 'Beautiful female examples: ' + mbtiInfo.female_examples;
    } else {
      femaleExamplesElement.textContent = '';
    }
    
    if (mbtiInfo.male_examples) {
      maleExamplesElement.textContent = 'Notable male examples: ' + mbtiInfo.male_examples;
    } else {
      maleExamplesElement.textContent = '';
    }
  } else {
    descriptionElement.textContent = 'Select an MBTI type to view the description.';
    acronymElement.textContent = '';
    celebritiesElement.textContent = '';
    femaleExamplesElement.textContent = '';
    maleExamplesElement.textContent = '';
  }
}

// Make mbtiTypes and handleMbtiSelection available globally
window.mbtiTypes = mbtiTypes;
window.handleMbtiSelection = handleMbtiSelection;

// If module exports are supported (for Node.js environments)
if (typeof module !== 'undefined') {
  module.exports = { mbtiTypes };
}
