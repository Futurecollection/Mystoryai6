
// Myers-Briggs personality types with descriptions and celebrity examples
window.mbtiTypes = {
  "INTJ": {
    name: "INTJ - The Architect",
    description: "Strategic thinkers with a talent for planning and innovative problem-solving. Independent, analytical, and often perfectionistic.",
    celebrities: "Female: Michelle Obama, Hillary Clinton, Jodie Foster | Male: Elon Musk, Mark Zuckerberg, Christopher Nolan",
    traits: "Reserved, analytical, strategic, independent, direct, perfectionist, skeptical, determined"
  },
  "INTP": {
    name: "INTP - The Logician",
    description: "Innovative inventors with an unquenchable thirst for knowledge. Analytical problem-solvers who value precision and logic over emotion.",
    celebrities: "Female: Marie Curie, Tina Fey, Angela Merkel | Male: Albert Einstein, Bill Gates, Larry Page",
    traits: "Quiet, analytical, curious, imaginative, flexible, theoretical, absent-minded, objective"
  },
  "ENTJ": {
    name: "ENTJ - The Commander",
    description: "Bold, imaginative, and strong-willed leaders who always find a way to achieve their goals. Natural strategic planners and executives.",
    celebrities: "Female: Margaret Thatcher, Oprah Winfrey, Whoopi Goldberg | Male: Steve Jobs, Franklin D. Roosevelt, Jack Welch",
    traits: "Confident, decisive, efficient, strategic, challenging, direct, objective, driven"
  },
  "ENTP": {
    name: "ENTP - The Debater",
    description: "Smart and curious thinkers who cannot resist an intellectual challenge. Natural brainstormers who enjoy exploring all possibilities.",
    celebrities: "Female: Amy Poehler, Gillian Anderson, Celine Dion | Male: Robert Downey Jr., Leonardo da Vinci, Thomas Edison",
    traits: "Quick-witted, creative, argumentative, theoretical, idea-focused, innovative, outspoken, adaptable"
  },
  "INFJ": {
    name: "INFJ - The Advocate",
    description: "Quiet idealists with a strong sense of morality and vision for how things could be. Private but deeply caring about others.",
    celebrities: "Female: Nicole Kidman, Cate Blanchett, Taylor Swift | Male: Martin Luther King Jr., Nelson Mandela, Plato",
    traits: "Reserved, insightful, idealistic, sensitive, principled, complex, creative, visionary"
  },
  "INFP": {
    name: "INFP - The Mediator",
    description: "Imaginative idealists guided by their values and principles. Seek meaning in connections with others and the world around them.",
    celebrities: "Female: Audrey Hepburn, Princess Diana, J.K. Rowling | Male: Johnny Depp, William Shakespeare, Tom Hiddleston",
    traits: "Idealistic, empathetic, creative, reserved, flexible, passionate, sensitive, dedicated"
  },
  "ENFJ": {
    name: "ENFJ - The Protagonist",
    description: "Charismatic leaders inspired to help others fulfill their potential. Natural communicators who value authentic connections.",
    celebrities: "Female: Jennifer Lawrence, Maya Angelou, Tyra Banks | Male: Barack Obama, Neil deGrasse Tyson, Dr. Phil McGraw",
    traits: "Empathetic, charismatic, persuasive, altruistic, diplomatic, organized, idealistic, warm"
  },
  "ENFP": {
    name: "ENFP - The Campaigner",
    description: "Enthusiastic, creative free spirits with an infectious energy. Value personal freedom and finding deeper meaning in life.",
    celebrities: "Female: Ellen DeGeneres, Sandra Bullock, Kelly Clarkson | Male: Robin Williams, Robert Downey Jr., Walt Disney",
    traits: "Enthusiastic, creative, sociable, perceptive, expressive, independent, spontaneous, optimistic"
  },
  "ISTJ": {
    name: "ISTJ - The Logistician",
    description: "Practical and detail-oriented individuals with a strong sense of duty. Value tradition, responsibility, and straightforwardness.",
    celebrities: "Female: Queen Elizabeth II, Angela Merkel, Natalie Portman | Male: Warren Buffett, Jeff Bezos, George Washington",
    traits: "Responsible, reliable, factual, practical, organized, traditional, logical, detail-oriented"
  },
  "ISFJ": {
    name: "ISFJ - The Defender",
    description: "Warm protectors dedicated to serving others. Extremely observant and practical, with excellent memory for details about people.",
    celebrities: "Female: Kate Middleton, Mother Teresa, Rosa Parks | Male: Tom Hanks, Vin Diesel, Dr. Ben Carson",
    traits: "Modest, loyal, considerate, patient, practical, supportive, meticulous, traditional"
  },
  "ESTJ": {
    name: "ESTJ - The Executive",
    description: "Decisive organizers who value clarity and structure. Natural leaders who implement practical solutions to real-world problems.",
    celebrities: "Female: Judge Judy, Sonia Sotomayor, Michelle Obama | Male: John D. Rockefeller, Frank Sinatra, James Monroe",
    traits: "Organized, practical, logical, objective, dutiful, traditional, direct, efficient"
  },
  "ESFJ": {
    name: "ESFJ - The Consul",
    description: "Caring and sociable traditionalists, eager to help others. Focused on maintaining harmony and supporting those in need.",
    celebrities: "Female: Jennifer Garner, Taylor Swift, Marie Osmond | Male: Bill Clinton, Hugh Jackman, Chris Evans",
    traits: "Friendly, responsible, reliable, organized, practical, supportive, sociable, traditional"
  },
  "ISTP": {
    name: "ISTP - The Virtuoso",
    description: "Bold explorers who love hands-on learning and problem-solving. Value efficiency and logical reasoning.",
    celebrities: "Female: Milla Jovovich, Scarlett Johansson, Kristen Stewart | Male: Michael Jordan, Tom Cruise, Bruce Lee",
    traits: "Calm, reserved, practical, logical, spontaneous, independent, adaptable, hands-on"
  },
  "ISFP": {
    name: "ISFP - The Adventurer",
    description: "Artistic experimenters living in the moment. Enjoy exploring with their senses and finding beauty in the unexpected.",
    celebrities: "Female: Britney Spears, Rihanna, Marilyn Monroe | Male: Bob Dylan, Michael Jackson, Kevin Costner",
    traits: "Sensitive, artistic, gentle, spontaneous, loyal, reserved, adaptable, practical"
  },
  "ESTP": {
    name: "ESTP - The Entrepreneur",
    description: "Smart, energetic risk-takers who live for the moment. Value freedom and solving problems in creative, unconventional ways.",
    celebrities: "Female: Madonna, Miley Cyrus, Pink | Male: Donald Trump, Ernest Hemingway, Eddie Murphy",
    traits: "Energetic, risk-taking, spontaneous, persuasive, practical, direct, observant, adaptable"
  },
  "ESFP": {
    name: "ESFP - The Entertainer",
    description: "Spontaneous performers who enjoy living in the moment and bringing joy to others. Enthusiastic, friendly fun-seekers.",
    celebrities: "Female: Marilyn Monroe, Adele, Katy Perry | Male: Jamie Foxx, Steve Irwin, Will Smith",
    traits: "Enthusiastic, fun-loving, spontaneous, friendly, sociable, charming, practical, observant"
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
}
