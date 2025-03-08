
// Myers-Briggs personality types with descriptions and celebrity examples
window.mbtiTypes = {
  "INTJ": {
    name: "The Architect",
    description: "Strategic thinkers with a plan for everything. Architects are independent, innovative problem-solvers with a natural confidence and an aura of mystery. They blend imagination and reliability.",
    celebrities: "Female: Natalie Portman, Cate Blanchett, Jodie Foster | Male: Elon Musk, Christopher Nolan, Benedict Cumberbatch",
    traits: "Reserved, analytical, strategic, independent, direct, perfectionist, skeptical, determined"
  },
  "INTP": {
    name: "The Logician",
    description: "Brilliant inventors with an unquenchable thirst for knowledge and elegant theories. Charismatically quirky with minds that never stop analyzing possibilities.",
    celebrities: "Female: Emma Watson, Tina Fey, Marie Curie | Male: Albert Einstein, Keanu Reeves, Tom Hiddleston",
    traits: "Quiet, analytical, curious, imaginative, flexible, theoretical, absent-minded, objective"
  },
  "ENTJ": {
    name: "The Commander",
    description: "Bold, charismatic leaders who effortlessly take charge and inspire others to follow their vision. Magnetic presence with unshakeable confidence.",
    celebrities: "Female: Charlize Theron, Oprah Winfrey, Emma Stone | Male: Steve Jobs, Harrison Ford, Gordon Ramsay",
    traits: "Confident, decisive, efficient, strategic, challenging, direct, objective, driven"
  },
  "ENTP": {
    name: "The Debater",
    description: "Charming visionaries who love intellectual challenges and see possibilities everywhere. Quick-witted and persuasive with an infectious energy.",
    celebrities: "Female: Amy Poehler, Elizabeth Olsen, Gillian Anderson | Male: Robert Downey Jr., Ryan Reynolds, Leonardo DiCaprio",
    traits: "Innovative, enthusiastic, strategic, versatile, argumentative, charismatic, adaptable, playful"
  },
  "INFJ": {
    name: "The Advocate",
    description: "Thoughtful idealists with deep insight into human nature. Advocates combine creativity with a strong moral compass and rare emotional intelligence.",
    celebrities: "Female: Nicole Kidman, Cate Blanchett, Emma Watson | Male: Benedict Cumberbatch, Jared Leto, Tom Hiddleston",
    traits: "Insightful, principled, creative, sensitive, reserved, inspiring, idealistic, complex"
  },
  "INFP": {
    name: "The Mediator",
    description: "Thoughtful dreamers with rich inner worlds. Mediators are empathetic, artistic souls who connect deeply with others while maintaining their unique perspective.",
    celebrities: "Female: Audrey Hepburn, Zooey Deschanel, Bjork | Male: Johnny Depp, Jude Law, Andrew Garfield",
    traits: "Idealistic, compassionate, creative, passionate, dedicated, adaptable, sensitive, introspective"
  },
  "ENFJ": {
    name: "The Protagonist",
    description: "Natural-born leaders with magnetic charisma and genuine warmth. Protagonists inspire others with their passion, authenticity, and ability to see potential.",
    celebrities: "Female: Jennifer Lawrence, Dakota Fanning, Zendaya | Male: Chris Evans, John Cusack, Ben Affleck",
    traits: "Charismatic, inspiring, empathetic, genuine, organized, diplomatic, altruistic, persuasive"
  },
  "ENFP": {
    name: "The Campaigner",
    description: "Free-spirited, charismatic individuals who light up any room they enter. Campaigners combine playful energy with deep emotional intelligence.",
    celebrities: "Female: Sandra Bullock, Jennifer Aniston, Margot Robbie | Male: Robert Downey Jr., Chris Pratt, Tom Holland",
    traits: "Enthusiastic, creative, sociable, energetic, perceptive, independent, adaptable, passionate"
  },
  "ISTJ": {
    name: "The Logistician",
    description: "Responsible, detail-oriented individuals with impressive reliability and quiet strength. Logisticians bring stability, organization, and dependability.",
    celebrities: "Female: Queen Elizabeth II, Natalie Portman, Kate Middleton | Male: Tom Hanks, Denzel Washington, Henry Cavill",
    traits: "Practical, reliable, organized, loyal, traditional, calm, honest, factual"
  },
  "ISFJ": {
    name: "The Defender",
    description: "Warm protectors with exceptional attention to detail. Defenders combine nurturing spirit with practical reliability and genuine commitment to those they care about.",
    celebrities: "Female: Anne Hathaway, Kate Middleton, Jessica Alba | Male: Tobey Maguire, Hugh Jackman, Ryan Gosling",
    traits: "Reliable, patient, supportive, humble, hardworking, loyal, practical, observant"
  },
  "ESTJ": {
    name: "The Executive",
    description: "Confident, decisive leaders who value tradition and order. Executives bring structure, clarity, and reliability to any environment with their practical approach.",
    celebrities: "Female: Emma Watson, Courteney Cox, Saoirse Ronan | Male: Chris Evans, Hugh Jackman, Frank Sinatra",
    traits: "Organized, dedicated, practical, direct, honest, structured, efficient, traditional"
  },
  "ESFJ": {
    name: "The Consul",
    description: "Caring, social, and organized individuals who love bringing people together. Consuls create harmony with their warmth, practicality, and reliable nature.",
    celebrities: "Female: Jennifer Garner, Reese Witherspoon, Taylor Swift | Male: Chris Evans, Hugh Jackman, Chris Hemsworth",
    traits: "Supportive, reliable, conscientious, structured, practical, warm, traditional, organized"
  },
  "ISTP": {
    name: "The Virtuoso",
    description: "Adventurous problem-solvers with a talent for tackling challenges. Virtuosos combine confident independence with a laid-back attitude and practical ingenuity.",
    celebrities: "Female: Scarlett Johansson, Olivia Wilde, Kristen Stewart | Male: Tom Cruise, Daniel Craig, Clint Eastwood",
    traits: "Adaptable, practical, rational, spontaneous, independent, adventurous, mechanical, logical"
  },
  "ISFP": {
    name: "The Adventurer",
    description: "Artistic free spirits with an understated charm. Adventurers approach life with quiet confidence, an eye for beauty, and a taste for authentic experiences.",
    celebrities: "Female: Zendaya, Bella Hadid, Selena Gomez | Male: Ryan Gosling, Liam Hemsworth, Justin Bieber",
    traits: "Creative, aesthetic, sensitive, spontaneous, passionate, gentle, practical, loyal"
  },
  "ESTP": {
    name: "The Entrepreneur",
    description: "Bold risk-takers who live in the moment with contagious energy. Entrepreneurs combine sharp observation skills, charisma, and a practical approach to problem-solving.",
    celebrities: "Female: Megan Fox, Madonna, Demi Moore | Male: Chris Hemsworth, Leonardo DiCaprio, Dave Franco",
    traits: "Energetic, adventurous, adaptable, perceptive, pragmatic, persuasive, spontaneous, analytical"
  },
  "ESFP": {
    name: "The Entertainer",
    description: "Spontaneous performers who bring joy to every situation. Entertainers combine magnetic charm with genuine warmth and an unmatched enthusiasm for life's pleasures.",
    celebrities: "Female: Mila Kunis, Miley Cyrus, Marilyn Monroe | Male: Chris Pratt, Jamie Foxx, Will Smith",
    traits: "Enthusiastic, charming, friendly, spontaneous, vibrant, imaginative, observant, practical"
  }
};

// Function to update the NPC biography based on MBTI personality
window.updateBioWithPersonality = function(bioText, personalityType) {
  if (!window.mbtiTypes || !window.mbtiTypes[personalityType]) {
    console.log("No valid personality type selected");
    return bioText;
  }
  
  const personality = window.mbtiTypes[personalityType];
  
  // Add MBTI-specific section to biography
  const mbtiSection = `\n\n## Personality Profile
${personalityType} - ${personality.name}
${personality.description}
Key traits: ${personality.traits}
Notable examples: ${personality.celebrities}`;
  
  return bioText + mbtiSection;
};

// Function to handle selection of an MBTI personality type
window.handleMbtiSelection = function(selectedType) {
  const mbtiDescription = document.getElementById('mbtiDescription');
  const mbtiCelebrities = document.getElementById('mbtiCelebrities');
  
  if (mbtiDescription && mbtiCelebrities && window.mbtiTypes[selectedType]) {
    const personality = window.mbtiTypes[selectedType];
    mbtiDescription.textContent = personality.description;
    mbtiCelebrities.textContent = "Notable examples: " + personality.celebrities;
  }
}
