
// Myers-Briggs personality types with descriptions and celebrity examples
window.mbtiTypes = {
  "INTJ": {
    name: "INTJ - The Architect",
    description: "Strategic thinkers with a talent for planning and innovative problem-solving. Independent, analytical, and often perfectionistic.",
    celebrities: "Elon Musk, Mark Zuckerberg, Christopher Nolan",
    traits: "Reserved, analytical, strategic, independent, direct, perfectionist, skeptical, determined"
  },
  "INTP": {
    name: "INTP - The Logician",
    description: "Innovative inventors with an unquenchable thirst for knowledge. Analytical problem-solvers who value precision and logic over emotion.",
    celebrities: "Albert Einstein, Bill Gates, Larry Page",
    traits: "Quiet, analytical, curious, imaginative, flexible, theoretical, absent-minded, objective"
  },
  "ENTJ": {
    name: "ENTJ - The Commander",
    description: "Bold, imaginative, and strong-willed leaders who always find a way to achieve their goals. Natural strategic planners and executives.",
    celebrities: "Steve Jobs, Margaret Thatcher, Franklin D. Roosevelt",
    traits: "Confident, decisive, efficient, strategic, challenging, direct, objective, driven"
  },
  "ENTP": {
    name: "ENTP - The Debater",
    description: "Smart and curious thinkers who cannot resist an intellectual challenge. Natural brainstormers who enjoy exploring all possibilities.",
    celebrities: "Robert Downey Jr., Leonardo da Vinci, Thomas Edison",
    traits: "Inventive, enthusiastic, debative, quick-thinking, outspoken, adaptable, playful, challenging"
  },
  "INFJ": {
    name: "INFJ - The Advocate",
    description: "Quiet idealists with deep insights and unwavering values. Seek meaning in connections and have a clear vision of how to serve humanity.",
    celebrities: "Nelson Mandela, Taylor Swift, Martin Luther King Jr.",
    traits: "Idealistic, empathetic, complex, principled, creative, insightful, private, perfectionistic"
  },
  "INFP": {
    name: "INFP - The Mediator",
    description: "Poetic, kind, and altruistic individuals who see special meaning in everything. Always looking for the good in people and situations.",
    celebrities: "J.R.R. Tolkien, Princess Diana, Johnny Depp",
    traits: "Idealistic, empathetic, authentic, creative, reserved, flexible, passionate, dreamy"
  },
  "ENFJ": {
    name: "ENFJ - The Protagonist",
    description: "Charismatic and inspiring leaders who mesmerize their listeners. Naturally attuned to others' emotions and incredibly persuasive.",
    celebrities: "Barack Obama, Oprah Winfrey, Jennifer Lawrence",
    traits: "Charismatic, empathetic, authentic, inspiring, organized, diplomatic, supportive, idealistic"
  },
  "ENFP": {
    name: "ENFP - The Campaigner",
    description: "Enthusiastic, creative, and sociable free spirits who find potential and inspiration everywhere. People-centered and passionate.",
    celebrities: "Robin Williams, Ellen DeGeneres, Robert Downey Jr.",
    traits: "Enthusiastic, creative, spontaneous, warm, perceptive, expressive, independent, optimistic"
  },
  "ISTJ": {
    name: "ISTJ - The Logistician",
    description: "Practical and fact-minded individuals whose reliability cannot be doubted. Take a methodical approach to achieving their goals.",
    celebrities: "Warren Buffett, Queen Elizabeth II, Jeff Bezos",
    traits: "Organized, reliable, practical, logical, systematic, detached, honest, traditional"
  },
  "ISFJ": {
    name: "ISFJ - The Defender",
    description: "Very dedicated and warm protectors who are always ready to defend their loved ones. Extraordinarily caring and social.",
    celebrities: "Mother Teresa, Kate Middleton, Beyoncé",
    traits: "Reliable, practical, detailed, observant, loyal, protective, humble, service-oriented"
  },
  "ESTJ": {
    name: "ESTJ - The Executive",
    description: "Excellent administrators, unsurpassed at managing things and people. Strong believers in tradition, hierarchy, and clear standards.",
    celebrities: "Judge Judy, Lyndon B. Johnson, Frank Sinatra",
    traits: "Organized, practical, honest, dedicated, dignified, traditional, direct, responsible"
  },
  "ESFJ": {
    name: "ESFJ - The Consul",
    description: "Extraordinarily caring, social, and popular people who are always eager to help. Tend to be the cornerstone of communities.",
    celebrities: "Jennifer Garner, Taylor Swift, Bill Clinton",
    traits: "Warm, loyal, organized, practical, sociable, responsible, traditional, considerate"
  },
  "ISTP": {
    name: "ISTP - The Virtuoso",
    description: "Bold and practical experimenters, masters of tools and machinery. Enjoy adventure and hands-on problem-solving.",
    celebrities: "Clint Eastwood, Tom Cruise, Michael Jordan",
    traits: "Practical, logical, spontaneous, independent, analytical, adaptable, adventurous, realistic"
  },
  "ISFP": {
    name: "ISFP - The Adventurer",
    description: "Flexible and charming artists who are always ready to explore and experience something new. Live in the moment and enjoy their surroundings.",
    celebrities: "Michael Jackson, Britney Spears, Bob Dylan",
    traits: "Artistic, gentle, loyal, adaptable, private, practical, spontaneous, sensitive"
  },
  "ESTP": {
    name: "ESTP - The Entrepreneur",
    description: "Smart, energetic, and very perceptive people who truly enjoy living on the edge. Pragmatic problem-solvers who love action.",
    celebrities: "Donald Trump, Madonna, Bruce Willis",
    traits: "Bold, pragmatic, energetic, persuasive, action-oriented, spontaneous, adaptable, risk-taking"
  },
  "ESFP": {
    name: "ESFP - The Entertainer",
    description: "Spontaneous, energetic, and enthusiastic entertainers who love being in the spotlight. Enjoy making others happy and living in the moment.",
    celebrities: "Adele, Jamie Foxx, Marilyn Monroe",
    traits: "Enthusiastic, fun-loving, social, spontaneous, warm, practical, observant, supportive"
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
Key traits: ${personality.traits}`;
  
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
