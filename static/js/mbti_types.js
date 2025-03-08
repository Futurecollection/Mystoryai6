
// Myers-Briggs personality types with descriptions and celebrity examples
window.mbtiTypes = {
  "INTJ": {
    name: "INTJ - The Architect",
    description: "Strategic visionaries with a masterful ability to plan and innovative problem-solving skills. Independent, intellectual, and naturally confident with a hint of mystery.",
    celebrities: "Female: Natalie Portman, Rooney Mara, Jodie Foster | Male: Henry Cavill, Christian Bale, Benedict Cumberbatch",
    traits: "Reserved, analytical, strategic, independent, direct, perfectionist, skeptical, determined"
  },
  "INTP": {
    name: "INTP - The Logician",
    description: "Brilliant inventors with an unquenchable thirst for knowledge and elegant theories. Charismatically quirky with minds that never stop analyzing possibilities.",
    celebrities: "Female: Emma Watson, Aubrey Plaza, Kristen Stewart | Male: Keanu Reeves, Tom Hiddleston, Jesse Eisenberg",
    traits: "Quiet, analytical, curious, imaginative, flexible, theoretical, absent-minded, objective"
  },
  "ENTJ": {
    name: "ENTJ - The Commander",
    description: "Bold, charismatic leaders who effortlessly take charge and inspire others to follow their vision. Magnetic presence with unshakeable confidence.",
    celebrities: "Female: Charlize Theron, Tyra Banks, Emma Stone | Male: Chris Evans, Leonardo DiCaprio, George Clooney",
    traits: "Confident, decisive, efficient, strategic, challenging, direct, objective, driven"
  },
  "ENTP": {
    name: "ENTP - The Debater",
    description: "Charming visionaries with quick wit and a talent for seeing connections others miss. Intellectually playful with a magnetic ability to engage others in their ideas.",
    celebrities: "Female: Elizabeth Olsen, Jennifer Lawrence, Amy Poehler | Male: Robert Downey Jr., Ryan Reynolds, Neil Patrick Harris",
    traits: "Charismatic, argumentative, enthusiastic, innovative, spontaneous, analytical, quick-witted, adaptable"
  },
  "INFJ": {
    name: "INFJ - The Advocate",
    description: "Mysterious and insightful with a deep understanding of human nature. Quietly captivating with an alluring depth that draws people in.",
    celebrities: "Female: Nicole Kidman, Carey Mulligan, Cate Blanchett | Male: Benedict Cumberbatch, Jamie Dornan, Jake Gyllenhaal",
    traits: "Private, idealistic, principled, creative, insightful, sensitive, contemplative, complex"
  },
  "INFP": {
    name: "INFP - The Mediator",
    description: "Enchanting dreamers with a rich inner world and deep capacity for connection. Their gentle authenticity and emotional depth makes them irresistibly intriguing.",
    celebrities: "Female: Audrey Hepburn, Zooey Deschanel, Dakota Fanning | Male: Johnny Depp, Timothée Chalamet, Andrew Garfield",
    traits: "Idealistic, creative, compassionate, sensitive, reserved, adaptable, open-minded, individualistic"
  },
  "ENFJ": {
    name: "ENFJ - The Protagonist",
    description: "Captivating, warm leaders who naturally inspire devotion. Their genuine charisma and ability to make others feel special creates instant magnetism.",
    celebrities: "Female: Jennifer Lawrence, Emma Stone, Taylor Swift | Male: Chris Hemsworth, Hugh Jackman, John Krasinski",
    traits: "Charismatic, empathetic, inspiring, diplomatic, passionate, warm, organized, articulate"
  },
  "ENFP": {
    name: "ENFP - The Campaigner",
    description: "Vibrant free spirits with contagious enthusiasm and charm. Their spontaneous passion and genuine interest in others makes them immediately likable and alluring.",
    celebrities: "Female: Margot Robbie, Zendaya, Sandra Bullock | Male: Chris Pratt, Tom Holland, Jason Segel",
    traits: "Enthusiastic, creative, sociable, expressive, warm, spontaneous, perceptive, adaptable"
  },
  "ISTJ": {
    name: "ISTJ - The Logistician",
    description: "Dependable and composed with a quiet strength that commands respect. Their reliability and attention to detail creates a compelling steadiness.",
    celebrities: "Female: Kate Middleton, Anne Hathaway, Michelle Obama | Male: Tom Cruise, Daniel Craig, Chris Evans",
    traits: "Practical, responsible, loyal, organized, factual, honest, detail-oriented, calm"
  },
  "ISFJ": {
    name: "ISFJ - The Defender",
    description: "Warm protectors with an intuitive understanding of others' needs. Their nurturing attention to detail and quiet devotion creates a deeply attractive stability.",
    celebrities: "Female: Kate Winslet, Jennifer Aniston, Halle Berry | Male: Ryan Gosling, Chris Pine, Hugh Jackman",
    traits: "Attentive, detailed, loyal, traditional, observant, supportive, patient, practical"
  },
  "ESTJ": {
    name: "ESTJ - The Executive",
    description: "Confident decision-makers with a commanding presence. Their practical leadership and direct approach creates an appealing sense of security and strength.",
    celebrities: "Female: Gal Gadot, Lucy Liu, Tyra Banks | Male: Chris Pratt, Dwayne Johnson, Mark Wahlberg",
    traits: "Organized, practical, direct, structured, traditional, loyal, efficient, decisive"
  },
  "ESFJ": {
    name: "ESFJ - The Consul",
    description: "Warm socialites with a natural ability to connect with others. Their attentive thoughtfulness and genuine care creates an attractive sense of belonging.",
    celebrities: "Female: Jennifer Garner, Reese Witherspoon, Selena Gomez | Male: Chris Evans, Hugh Jackman, Justin Timberlake",
    traits: "Supportive, popular, practical, harmonious, organized, sociable, caring, traditional"
  },
  "ISTP": {
    name: "ISTP - The Virtuoso",
    description: "Cool problem-solvers with a quiet sense of adventure. Their skilled competence and laid-back confidence creates an effortlessly attractive aura.",
    celebrities: "Female: Scarlett Johansson, Kristen Stewart, Angelina Jolie | Male: Tom Hardy, Daniel Craig, Channing Tatum",
    traits: "Adaptable, rational, practical, spontaneous, independent, reserved, hands-on, adventurous"
  },
  "ISFP": {
    name: "ISFP - The Adventurer",
    description: "Artistic free spirits with a quiet sensuality. Their authentic expression and in-the-moment presence creates a naturally seductive appeal.",
    celebrities: "Female: Zoe Kravitz, Kendall Jenner, Rihanna | Male: Michael B. Jordan, Liam Hemsworth, Zac Efron",
    traits: "Artistic, sensitive, passionate, spontaneous, gentle, adventurous, harmonious, independent"
  },
  "ESTP": {
    name: "ESTP - The Entrepreneur",
    description: "Bold thrill-seekers with magnetic charisma. Their spontaneous energy and confident risk-taking creates an irresistible excitement.",
    celebrities: "Female: Megan Fox, Miley Cyrus, Madonna | Male: Chris Hemsworth, Tom Cruise, Channing Tatum",
    traits: "Energetic, risk-taking, direct, spontaneous, adaptable, charming, persuasive, observant"
  },
  "ESFP": {
    name: "ESFP - The Entertainer",
    description: "Vibrant performers with an irresistible zest for life. Their spontaneous passion and genuine warmth creates an immediate attraction.",
    celebrities: "Female: Margot Robbie, Jennifer Lopez, Katy Perry | Male: Ryan Reynolds, Chris Hemsworth, Zac Efron",
    traits: "Enthusiastic, spontaneous, fun-loving, friendly, charming, practical, stylish, energetic"
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
    mbtiCelebrities.textContent = "Famous examples: " + personality.celebrities;
  } else {
    console.log("Could not find MBTI data for type:", selectedType);
    if (mbtiDescription) mbtiDescription.textContent = "No description available for this type";
    if (mbtiCelebrities) mbtiCelebrities.textContent = "";
  }
}
