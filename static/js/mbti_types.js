const mbtiTypes = {
  "INTJ": {
    "name": "The Architect",
    "description": "INTJs are analytical problem-solvers, eager to improve systems and processes with their innovative ideas. They have a talent for seeing possibilities for improvement, whether at work, at home, or in themselves. Often intellectual, INTJs enjoy logical reasoning and complex problem-solving.",
    "celebrities": "Elon Musk, Mark Zuckerberg, Christopher Nolan, Jay-Z"
  },
  "INTP": {
    "name": "The Logician",
    "description": "INTPs are innovative inventors with an unquenchable thirst for knowledge. They are known for their brilliant theories and unrelenting logic. They love patterns and have an eye for spotting logical discrepancies. They often lose themselves in thought, which can make them appear detached or aloof.",
    "celebrities": "Albert Einstein, Bill Gates, Isaac Newton, Marie Curie"
  },
  "ENTJ": {
    "name": "The Commander",
    "description": "ENTJs are bold, imaginative, and strong-willed leaders, always finding a way or making one. They are natural-born leaders who embody charisma and confidence, projecting authority in a way that draws crowds together. However, they can be intimidating and overly dominant.",
    "celebrities": "Steve Jobs, Margaret Thatcher, Gordon Ramsay, Jim Carrey"
  },
  "ENTP": {
    "name": "The Debater",
    "description": "ENTPs are smart, curious thinkers who cannot resist an intellectual challenge. They are typically original, creative, and resourceful in solving new and challenging problems. They enjoy the mental exercise of questioning the established way of doing things and exploring alternatives.",
    "celebrities": "Leonardo da Vinci, Thomas Edison, Robert Downey Jr., Jon Stewart"
  },
  "INFJ": {
    "name": "The Advocate",
    "description": "INFJs are creative nurturers with a strong sense of personal integrity and a drive to help others realize their potential. They have an intuitive understanding of complex people issues and naturally see things from multiple perspectives. They are generally idealistic and deeply concerned about the state of humanity.",
    "celebrities": "Martin Luther King Jr., Nelson Mandela, Lady Gaga, Nicole Kidman"
  },
  "INFP": {
    "name": "The Mediator",
    "description": "INFPs are imaginative idealists guided by their own core values and beliefs. They are sensitive, caring, and compassionate, and deeply concerned with personal growth. They typically strive to discover their place in the world and understand the purpose of their lives.",
    "celebrities": "William Shakespeare, J.R.R. Tolkien, Johnny Depp, Audrey Hepburn"
  },
  "ENFJ": {
    "name": "The Protagonist",
    "description": "ENFJs are charismatic and inspiring leaders, able to mesmerize their listeners. They are typically focused on bringing out the best in others, finding ways to help them reach their full potential. They can be powerful motivators, often expressing genuine concern for others.",
    "celebrities": "Barack Obama, Oprah Winfrey, Ben Affleck, Jennifer Lawrence"
  },
  "ENFP": {
    "name": "The Campaigner",
    "description": "ENFPs are enthusiastic, creative, and sociable free spirits who can always find a reason to smile. They are warm, passionate people, known for their empathy and ability to inspire others. They are curious about others and enjoy exploring alternative possibilities and ideas.",
    "celebrities": "Robin Williams, Robert Downey Jr., Sandra Bullock, Will Smith"
  },
  "ISTJ": {
    "name": "The Logistician",
    "description": "ISTJs are practical, fact-minded individuals, whose reliability cannot be doubted. They are dependable, practical, and often traditional, valuing loyalty and hard work. They prefer to be thorough, precise, and operate by the book, with a strong sense of duty.",
    "celebrities": "Queen Elizabeth II, Natalie Portman, Jeff Bezos, Warren Buffett"
  },
  "ISFJ": {
    "name": "The Defender",
    "description": "ISFJs are warm protectors, ready to defend their loved ones. They are supportive, reliable, patient, and devoted, typically putting the needs of others above their own. They value harmony and cooperation and typically work hard to achieve them.",
    "celebrities": "Mother Teresa, Kate Middleton, Beyoncé, Aretha Franklin"
  },
  "ESTJ": {
    "name": "The Executive",
    "description": "ESTJs are excellent administrators, unsurpassed at managing things or people. They are conventional, factual, and grounded in reality, preferring traditional hierarchies and doing things by the book. They value predictability and prefer to go about things methodically.",
    "celebrities": "Judge Judy, Sonia Sotomayor, John D. Rockefeller, Frank Sinatra"
  },
  "ESFJ": {
    "name": "The Consul",
    "description": "ESFJs are extraordinarily caring, social, and popular people, always eager to help. They are attentive to the needs of others and are often seen as sociable, organized, and dependable. They value harmony and cooperation and work hard to achieve it.",
    "celebrities": "Taylor Swift, Hugh Jackman, Jennifer Garner, Bill Clinton"
  },
  "ISTP": {
    "name": "The Virtuoso",
    "description": "ISTPs are bold and practical experimenters, masters of all kinds of tools. They are typically reserved yet adventurous, loyal to their peers but guarded in expressing emotions. They excel at analyzing situations and implementing practical solutions.",
    "celebrities": "Michael Jordan, Tom Cruise, Clint Eastwood, Milla Jovovich"
  },
  "ISFP": {
    "name": "The Adventurer",
    "description": "ISFPs are flexible, charming artists, always ready to explore and experience something new. They are sensitive to the needs of others, cooperative, and loyal. They value harmony, beauty, kindness, and experiencing life to its fullest.",
    "celebrities": "Bob Dylan, Lana Del Rey, Britney Spears, Kevin Costner"
  },
  "ESTP": {
    "name": "The Entrepreneur",
    "description": "ESTPs are smart, energetic makers who truly enjoy living on the edge. They are action-oriented, resourceful, and bold. They focus on immediate results, are spontaneous risk-takers, and excel at solving practical problems rather than theoretical ones.",
    "celebrities": "Donald Trump, Madonna, Jack Nicholson, Bruce Willis"
  },
  "ESFP": {
    "name": "The Entertainer",
    "description": "ESFPs are spontaneous, energetic entertainers who truly enjoy living in the moment. They are enthusiastic, friendly, and tactful with a strong sense of style. They enjoy being the center of attention and have a playful view of the world.",
    "celebrities": "Adele, Jamie Foxx, Marilyn Monroe, Elvis Presley"
  }
};

// Make the mbtiTypes available to other scripts
if (typeof module !== 'undefined') {
  module.exports = { mbtiTypes };
}

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