
// Define MBTI types with detailed descriptions
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
    "description": "ENTPs are smart and curious thinkers who cannot resist an intellectual challenge. They're quick-witted and resourceful, able to generate conceptual possibilities and then analyze them strategically. They love to debate ideas and may sometimes argue both sides for fun.",
    "celebrities": "Leonardo da Vinci, Tony Stark, Neil deGrasse Tyson"
  },
  "INFJ": {
    "name": "The Advocate",
    "description": "INFJs are quiet, mystical, and creative idealists with a strong sense of vision. They are deeply concerned about personal growth and contributing to the greater good. They are capable of profound insights into human nature and often act as quiet catalysts for positive change.",
    "celebrities": "Martin Luther King Jr., Taylor Swift, Atticus Finch"
  },
  "INFP": {
    "name": "The Mediator",
    "description": "INFPs are poetic, kind, and altruistic people, always looking to help a good cause. They see the world as a place of ideals and possibilities. They are deeply empathetic and driven by their values, seeking to understand themselves and those around them on a profound level.",
    "celebrities": "William Shakespeare, J.R.R. Tolkien, Princess Diana"
  },
  "ENFJ": {
    "name": "The Protagonist",
    "description": "ENFJs are charismatic and inspiring leaders who can mesmerize their listeners. Natural-born leaders full of passion and charisma, they can talk their way in or out of anything. They tend to value harmony and cooperation, often acting as catalysts for change.",
    "celebrities": "Barack Obama, Oprah Winfrey, Pope John Paul II"
  },
  "ENFP": {
    "name": "The Campaigner",
    "description": "ENFPs are enthusiastic, creative, and sociable free spirits who can always find a reason to smile. They're warmly enthusiastic and imaginative, seeing life as full of possibilities. They make connections between events and information very quickly and confidently proceed based on patterns they see.",
    "celebrities": "Robert Downey Jr., Ellen DeGeneres, Robin Williams"
  },
  "ISTJ": {
    "name": "The Logistician",
    "description": "ISTJs are practical and fact-minded individuals whose reliability cannot be doubted. They are responsible, organized, and methodical in their approach to life and work. They value traditions and loyalty, often serving as the quiet backbone of organizations and families.",
    "celebrities": "Queen Elizabeth II, George Washington, Jeff Bezos"
  },
  "ISFJ": {
    "name": "The Defender",
    "description": "ISFJs are very dedicated and warm protectors, always ready to defend their loved ones. They're quiet, kind, and conscientious. These individuals take their responsibilities seriously and can be counted on to follow through. They're often the unsung heroes who keep things running smoothly.",
    "celebrities": "Mother Teresa, Queen Elizabeth II, Kate Middleton"
  },
  "ESTJ": {
    "name": "The Executive",
    "description": "ESTJs are excellent administrators, unsurpassed at managing things or people. They're organized, honest, dedicated, and dignified. Taking their responsibilities seriously, they place high value on traditions and institutions. They believe in following rules and expect others to do the same.",
    "celebrities": "Michelle Obama, Judge Judy, John D. Rockefeller"
  },
  "ESFJ": {
    "name": "The Consul",
    "description": "ESFJs are extraordinarily caring, social, and popular people who are always eager to help. They're warm-hearted, conscientious, and cooperative. Valuing tradition and security, they're focused on fulfilling their duties and obligations. They seek to foster harmonious relationships in their lives.",
    "celebrities": "Jennifer Lopez, Taylor Swift, Bill Clinton"
  },
  "ISTP": {
    "name": "The Virtuoso",
    "description": "ISTPs are bold and practical experimenters, masters of all kinds of tools. They're quiet observers until a problem appears, then they act quickly to find a workable solution. They're analytical troubleshooters who excel at getting to the heart of practical matters.",
    "celebrities": "Bear Grylls, Michael Jordan, Clint Eastwood"
  },
  "ISFP": {
    "name": "The Adventurer",
    "description": "ISFPs are flexible and charming artists, always ready to explore and experience something new. They're quiet, sensitive, kind, and modest about their abilities. They enjoy the present moment and what's going on around them, often having a special affinity for aesthetics and natural harmony.",
    "celebrities": "Michael Jackson, David Beckham, Kevin Costner"
  },
  "ESTP": {
    "name": "The Entrepreneur",
    "description": "ESTPs are smart, energetic, and perceptive people who truly enjoy living on the edge. They're adaptable, resourceful, and focused on immediate results. They're risk-takers who live in the present moment, bringing a practical approach to problem-solving.",
    "celebrities": "Donald Trump, Ernest Hemingway, Madonna"
  },
  "ESFP": {
    "name": "The Entertainer",
    "description": "ESFPs are spontaneous, energetic, and enthusiastic people – life is never boring around them. They're outgoing, friendly, and accepting. They bring a playful, optimistic approach to life, enjoying each moment and making the most of every experience.",
    "celebrities": "Marilyn Monroe, Jamie Oliver, Miley Cyrus"
  }
};

// Function to handle MBTI selection
function handleMbtiSelection(mbtiType) {
  const descriptionElement = document.getElementById('mbtiDescription');
  const celebritiesElement = document.getElementById('mbtiCelebrities');
  
  if (mbtiType && mbtiTypes && mbtiTypes[mbtiType]) {
    const mbtiInfo = mbtiTypes[mbtiType];
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
}

// Make mbtiTypes and handleMbtiSelection available globally
window.mbtiTypes = mbtiTypes;
window.handleMbtiSelection = handleMbtiSelection;

// If module exports are supported (for Node.js environments)
if (typeof module !== 'undefined') {
  module.exports = { mbtiTypes };
}
