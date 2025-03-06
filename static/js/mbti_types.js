
// Myers-Briggs personality types with descriptions and celebrity examples
window.mbtiTypes = {
  "INTJ": {
    name: "INTJ - The Architect",
    description: "Strategic thinkers with a plan for everything. Architects are independent, innovative problem-solvers with a natural confidence and an aura of mystery. They blend imagination and reliability.",
    celebrities: "Female: Natalie Portman, Cate Blanchett, Jodie Foster | Male: Elon Musk, Christopher Nolan, Benedict Cumberbatch",
    traits: "Reserved, analytical, strategic, independent, direct, perfectionist, skeptical, determined"
  },
  "INTP": {
    name: "INTP - The Logician",
    description: "Brilliant inventors with an unquenchable thirst for knowledge and elegant theories. Charismatically quirky with minds that never stop analyzing possibilities.",
    celebrities: "Female: Emma Watson, Tina Fey, Marie Curie | Male: Albert Einstein, Keanu Reeves, Tom Hiddleston",
    traits: "Quiet, analytical, curious, imaginative, flexible, theoretical, absent-minded, objective"
  },
  "ENTJ": {
    name: "ENTJ - The Commander",
    description: "Bold, charismatic leaders who effortlessly take charge and inspire others to follow their vision. Magnetic presence with unshakeable confidence.",
    celebrities: "Female: Charlize Theron, Oprah Winfrey, Emma Stone | Male: Steve Jobs, Harrison Ford, Gordon Ramsay",
    traits: "Confident, decisive, efficient, strategic, challenging, direct, objective, driven"
  },
  "ENTP": {
    name: "ENTP - The Debater",
    description: "Quick-thinking challengers who love playing devil's advocate. Debaters bring innovative solutions through their enthusiasm for intellectual sparring and thinking outside the box.",
    celebrities: "Female: Amy Poehler, Gillian Anderson, Salma Hayek | Male: Robert Downey Jr., Ryan Reynolds, Leonardo DiCaprio",
    traits: "Enthusiastic, argumentative, charming, spontaneous, analytical, witty, adaptable, challenging"
  },
  "INFJ": {
    name: "INFJ - The Advocate",
    description: "Quiet visionaries with deep empathy and unwavering dedication to their values. Advocates combine creativity with principle, offering unique insights and genuine connection.",
    celebrities: "Female: Nicole Kidman, Lady Gaga, Rose Namajunas | Male: Benedict Cumberbatch, Jon Snow, Matthew McConaughey",
    traits: "Insightful, principled, creative, sensitive, reserved, idealistic, complex, determined"
  },
  "INFP": {
    name: "INFP - The Mediator",
    description: "Thoughtful idealists with an artistic spirit and profound emotional depth. Mediators see special potential in everyone and everything, dreaming of a world aligned with their inner values.",
    celebrities: "Female: Audrey Hepburn, Dakota Fanning, Princess Diana | Male: Johnny Depp, Andrew Garfield, Tom Hiddleston",
    traits: "Idealistic, empathetic, creative, passionate, loyal, adaptable, reserved, thoughtful"
  },
  "ENFJ": {
    name: "ENFJ - The Protagonist",
    description: "Charismatic inspirers who naturally lead others toward growth and fulfillment. Protagonists combine warmth with visionary thinking, bringing people together for a shared purpose.",
    celebrities: "Female: Jennifer Lawrence, Dakota Johnson, Emma Stone | Male: John Cusack, Ben Affleck, Bono",
    traits: "Charismatic, empathetic, organized, idealistic, persuasive, diplomatic, affirming, decisive"
  },
  "ENFP": {
    name: "ENFP - The Campaigner",
    description: "Enthusiastic free spirits with contagious energy and creativity. Campaigners see exciting possibilities everywhere and inspire others with their genuine warmth and passion.",
    celebrities: "Female: Zendaya, Gigi Hadid, Sandra Bullock | Male: Robert Pattinson, Oscar Isaac, Will Smith",
    traits: "Enthusiastic, imaginative, spontaneous, caring, perceptive, individualistic, expressive, independent"
  },
  "ISTJ": {
    name: "ISTJ - The Logistician",
    description: "Reliable realists who value tradition and create stability through meticulous attention to detail. Logisticians bring practical solutions and steadfast dependability.",
    celebrities: "Female: Natalie Portman, Queen Elizabeth II, Hermione Granger | Male: Denzel Washington, Tom Hanks, Christopher Nolan",
    traits: "Organized, practical, reliable, traditional, factual, logical, meticulous, reserved"
  },
  "ISFJ": {
    name: "ISFJ - The Defender",
    description: "Protective nurturers with an exceptional memory for personal details. Defenders create harmony through practical care, anticipating needs and quietly supporting others.",
    celebrities: "Female: Kate Middleton, Taylor Swift, Anne Hathaway | Male: Ryan Gosling, Hugh Jackman, Tobey Maguire",
    traits: "Supportive, practical, reliable, observant, detail-oriented, protective, traditional, humble"
  },
  "ESTJ": {
    name: "ESTJ - The Executive",
    description: "Efficient organizers who excel at turning plans into action. Executives bring structure and reliability, taking charge to ensure traditions and standards are upheld.",
    celebrities: "Female: Saoirse Ronan, Emma Watson, Judge Judy | Male: John Cena, Frank Sinatra, Dr. Phil",
    traits: "Organized, practical, direct, structured, loyal, traditional, responsible, decisive"
  },
  "ESFJ": {
    name: "ESFJ - The Consul",
    description: "Caring connectors who create harmony through practical service. Consuls excel at bringing people together, remembering details, and ensuring everyone feels valued.",
    celebrities: "Female: Jennifer Garner, Selena Gomez, Taylor Swift | Male: Chris Evans, Hugh Jackman, Bill Clinton",
    traits: "Supportive, reliable, conscientious, organized, warm, traditional, sociable, practical"
  },
  "ISTP": {
    name: "ISTP - The Virtuoso",
    description: "Adaptable troubleshooters with unmatched technical expertise. Virtuosos approach life with quiet curiosity, responding to challenges with cool efficiency and practical solutions.",
    celebrities: "Female: Scarlett Johansson, Kendall Jenner, Kristen Stewart | Male: Tom Cruise, Christian Bale, Michael Jordan",
    traits: "Practical, logical, adaptable, observant, independent, spontaneous, calm, analytical"
  },
  "ISFP": {
    name: "ISFP - The Adventurer",
    description: "Gentle artists with a strong aesthetic sense and quiet passion. Adventurers live in the moment, bringing beauty and kindness through their authentic self-expression.",
    celebrities: "Female: Beyoncé, Winona Ryder, Rihanna | Male: Michael Jackson, Jude Law, Liam Hemsworth",
    traits: "Artistic, sensitive, gentle, spontaneous, loyal, adaptable, private, passionate"
  },
  "ESTP": {
    name: "ESTP - The Entrepreneur",
    description: "Energetic thrill-seekers who excel in dynamic environments. Entrepreneurs solve problems with bold action, bringing charisma and practical intelligence to every challenge.",
    celebrities: "Female: Madonna, Megan Fox, Ruby Rose | Male: Conor McGregor, Donald Trump, Bruce Willis",
    traits: "Energetic, risk-taking, practical, persuasive, adaptable, resourceful, straightforward, observant"
  },
  "ESFP": {
    name: "ESFP - The Entertainer",
    description: "Spontaneous performers who bring contagious enthusiasm to life. Entertainers live for the moment, creating joy through their warmth, style, and practical approach to fun.",
    celebrities: "Female: Miley Cyrus, Margot Robbie, Adele | Male: Jamie Foxx, Chris Hemsworth, Leonardo DiCaprio",
    traits: "Enthusiastic, energetic, adaptable, friendly, practical, spontaneous, observant, stylish"
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
${personality.name}
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
};
