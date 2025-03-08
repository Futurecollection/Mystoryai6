
// Myers-Briggs personality types with descriptions and celebrity examples
window.mbtiTypes = {
  "INTJ": {
    name: "INTJ - The Mastermind",
    description: "INTJs are analytical problem-solvers, eager to improve systems and processes with their innovative ideas. They have a talent for seeing possibilities for improvement, whether at work, at home, or in themselves.",
    celebrities: "Female: Natalie Portman, Rooney Mara, Jodie Foster | Male: Henry Cavill, Christopher Nolan, Elon Musk",
    traits: "Strategic, independent, innovative, analytical, determined, perfectionist"
  },
  "INTP": {
    name: "INTP - The Architect",
    description: "INTPs are philosophical innovators, fascinated by logical analysis, systems, and design. They are preoccupied with theory, and search for the universal law behind everything they see. They want to understand the unifying themes of life, in all their complexity.",
    celebrities: "Female: Emma Watson, Marie Curie, Tina Fey | Male: Albert Einstein, Bill Gates, Keanu Reeves",
    traits: "Logical, analytical, curious, theoretical, abstract, imaginative"
  },
  "ENTJ": {
    name: "ENTJ - The Commander",
    description: "ENTJs are strategic leaders, motivated to organize change. They are quick to see inefficiency and conceptualize new solutions, and enjoy developing long-range plans to accomplish their vision. They excel at logical reasoning and are usually articulate and quick-witted.",
    celebrities: "Female: Charlize Theron, Margaret Thatcher, Whoopi Goldberg | Male: Steve Jobs, Gordon Ramsay, Jim Carrey",
    traits: "Confident, decisive, efficient, strategic, challenging, direct"
  },
  "ENTP": {
    name: "ENTP - The Visionary",
    description: "ENTPs are inspired innovators, motivated to find new solutions to intellectually challenging problems. They are curious and clever, and seek to comprehend the people, systems, and principles that surround them.",
    celebrities: "Female: Amy Poehler, Elizabeth Olsen, Celine Dion | Male: Robert Downey Jr., Leonardo DiCaprio, Ryan Reynolds",
    traits: "Innovative, resourceful, adaptable, enthusiastic, theoretical, analytical"
  },
  "INFJ": {
    name: "INFJ - The Counselor",
    description: "INFJs are creative nurturers with a strong sense of personal integrity and a drive to help others realize their potential. Creative and dedicated, they have a talent for helping others with original solutions to their personal challenges.",
    celebrities: "Female: Nicole Kidman, Cate Blanchett, Taylor Swift | Male: Benedict Cumberbatch, Martin Luther King Jr., Jon Snow",
    traits: "Insightful, creative, principled, empathetic, altruistic, complex"
  },
  "INFP": {
    name: "INFP - The Healer",
    description: "INFPs are imaginative idealists, guided by their own core values and beliefs. To a Healer, possibilities are paramount; the reality of the moment is only of passing concern. They see potential for a better future, and pursue truth and meaning with their own flair.",
    celebrities: "Female: Audrey Hepburn, Bjork, Lisa Kudrow | Male: Johnny Depp, Kurt Cobain, William Shakespeare",
    traits: "Idealistic, empathetic, creative, introspective, authentic, harmonious"
  },
  "ENFJ": {
    name: "ENFJ - The Teacher",
    description: "ENFJs are idealist organizers, driven to implement their vision of what is best for humanity. They often act as catalysts for human growth because of their ability to see potential in other people and their charisma in inspiring others to their ideas.",
    celebrities: "Female: Oprah Winfrey, Jennifer Lawrence, Maya Angelou | Male: Barack Obama, Ben Affleck, John Cusack",
    traits: "Charismatic, empathetic, diplomatic, responsible, idealistic, expressive"
  },
  "ENFP": {
    name: "ENFP - The Champion",
    description: "ENFPs are people-centered creators with a focus on possibilities and a contagious enthusiasm for new ideas, people and activities. Energetic, warm, and passionate, ENFPs love to help other people explore their creative potential.",
    celebrities: "Female: Sandra Bullock, Ellen DeGeneres, Kelly Clarkson | Male: Robin Williams, Robert Downey Jr., Will Smith",
    traits: "Enthusiastic, creative, spontaneous, optimistic, supportive, playful"
  },
  "ISTJ": {
    name: "ISTJ - The Inspector",
    description: "ISTJs are responsible organizers, driven to create and enforce order within systems and institutions. They are neat and orderly, inside and out, with a place for everything and everything in its place.",
    celebrities: "Female: Queen Elizabeth II, Natalie Portman, Kate Middleton | Male: Denzel Washington, Tom Hanks, Sting",
    traits: "Practical, reliable, thorough, logical, consistent, organized"
  },
  "ISFJ": {
    name: "ISFJ - The Protector",
    description: "ISFJs are industrious caretakers, loyal to traditions and organizations. They are practical, compassionate, and caring, and are motivated to provide for others and protect them from the dangers of life.",
    celebrities: "Female: Kate Middleton, Anne Hathaway, Mother Teresa | Male: Dr. Phil McGraw, Hank Hill, Tobey Maguire",
    traits: "Reliable, practical, observant, patient, devoted, protective"
  },
  "ESTJ": {
    name: "ESTJ - The Supervisor",
    description: "ESTJs are hardworking traditionalists, eager to take charge in organizing projects and people. Orderly, rule-abiding, and conscientious, they like to get things done, and tend to go about projects in a systematic, methodical way.",
    celebrities: "Female: Judge Judy, Sonia Sotomayor, Lucy Liu | Male: John D. Rockefeller, Tom Clancy, Frank Sinatra",
    traits: "Organized, practical, dependable, efficient, logical, straightforward"
  },
  "ESFJ": {
    name: "ESFJ - The Provider",
    description: "ESFJs are conscientious helpers, sensitive to the needs of others and energetically dedicated to their responsibilities. They excel at building community and bringing people together, often taking on the role of organizing gatherings and events.",
    celebrities: "Female: Jennifer Garner, Jennifer Lopez, Britney Spears | Male: Hugh Jackman, Steve Harvey, Patrick Stewart",
    traits: "Friendly, organized, dependable, practical, cooperative, loyal"
  },
  "ISTP": {
    name: "ISTP - The Craftsman",
    description: "ISTPs are observant artisans with an understanding of mechanics and an interest in troubleshooting. They approach their environments with a flexible logic, looking for practical solutions to the problems at hand.",
    celebrities: "Female: Scarlett Johansson, Demi Moore, Ellen Page | Male: Tom Cruise, Clint Eastwood, Michael Jordan",
    traits: "Adaptable, practical, logical, observant, analytical, independent"
  },
  "ISFP": {
    name: "ISFP - The Composer",
    description: "ISFPs are gentle caretakers who live in the present moment and enjoy their surroundings with cheerful, low-key enthusiasm. They are flexible and spontaneous, and like to go with the flow to enjoy what life has to offer.",
    celebrities: "Female: Marilyn Monroe, Britney Spears, Nicole Kidman | Male: Michael Jackson, Kevin Costner, Jimi Hendrix",
    traits: "Artistic, sensitive, gentle, spontaneous, reserved, authentic"
  },
  "ESTP": {
    name: "ESTP - The Dynamo",
    description: "ESTPs are energetic thrill seekers who are at their best when putting out fires, whether literal or metaphorical. They bring a sense of dynamic energy to their interactions with others and the world around them.",
    celebrities: "Female: Madonna, Mila Kunis, Miley Cyrus | Male: Donald Trump, Bruce Willis, Eddie Murphy",
    traits: "Energetic, adaptable, action-oriented, spontaneous, pragmatic, persuasive"
  },
  "ESFP": {
    name: "ESFP - The Performer",
    description: "ESFPs are vivacious entertainers who charm and engage those around them. They are spontaneous, energetic, and fun-loving, and take pleasure in the things around them: food, clothes, nature, animals, and especially people.",
    celebrities: "Female: Marilyn Monroe, Adele, Katy Perry | Male: Jamie Foxx, Elvis Presley, Justin Bieber",
    traits: "Enthusiastic, fun-loving, spontaneous, friendly, adaptable, lively"
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
};
