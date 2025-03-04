
// Character data structures for pre-made bios
const characterBios = {
  // Tech CEO - Emma
  "emma": {
    bio: `Emma Chen is a 32-year-old tech CEO who has transformed her startup into one of Silicon Valley's most innovative companies. With sleek black hair typically worn in a sophisticated low bun, striking amber eyes, and a confident smile, she commands attention in any room. Standing at 5'7" with an athletic build maintained through dawn yoga and evening runs, she carries herself with unmistakable poise. Emma typically dresses in tailored blazers, silk blouses, and slim pants, with a signature gold pendant necklace that was her grandmother's. She's known for her sharp intellect, strategic thinking, and surprising warmth once you break through her professional exterior. Between board meetings and product launches, she's looking for someone who can keep up with her fast-paced lifestyle but also remind her to slow down and enjoy life's simpler pleasures.`,

    // Character attributes
    name: "Emma Chen",
    gender: "Female",
    age: "32",
    ethnicity: "Chinese American",
    sexual_orientation: "Straight",
    relationship_goal: "Casual Dating",
    body_type: "Athletic",
    hair_color: "Black",
    hair_style: "Sophisticated low bun",
    personality: "Confident and Ambitious",
    clothing: "Tailored blazers and silk blouses",
    occupation: "Tech CEO",
    current_situation: "Career-focused",

    // Environment details
    environment: "Upscale Wine Bar",
    encounter_context: "Mutual Friend's Introduction"
  },
  
  // Hollywood Actress - Scarlett
  "scarlett": {
    bio: `Scarlett Winters, 28, is a rising Hollywood actress known for her breakout roles in indie films that have recently caught mainstream attention. With her wavy auburn hair that falls just past her shoulders, emerald green eyes, and a graceful presence, she stands out even in a city of beautiful people. She maintains her toned physique through dance and pilates, combining strength with elegant movement. Scarlett typically dresses in bohemian-inspired outfits when off-set - flowing dresses or vintage jeans with artsy tops, always with her signature constellation pendant. Behind her glamorous career, she's surprisingly down-to-earth, with a quick wit and genuine curiosity about people and their stories. Between filming locations and auditions, she's looking for someone authentic who values her for more than her rising fame, someone who can be her anchor in an industry known for its superficiality.`,

    name: "Scarlett Winters",
    gender: "Female",
    age: "28",
    ethnicity: "Irish American",
    sexual_orientation: "Straight",
    relationship_goal: "Serious Relationship",
    body_type: "Toned",
    hair_color: "Auburn",
    hair_style: "Wavy, shoulder-length",
    personality: "Genuine and Quick-witted",
    clothing: "Bohemian-inspired outfits",
    occupation: "Actress",
    current_situation: "Career on the rise",
    
    environment: "Exclusive Rooftop Bar",
    encounter_context: "Industry Party"
  },
  
  // Fashion Designer - Zendaya 
  "zendaya": {
    bio: `Zendaya Coleman, 25, is an innovative fashion designer whose bold, multicultural-inspired collections have taken the industry by storm. With her natural curly hair styled in various creative ways, deep brown eyes that miss no detail, and flawless dark skin, she embodies the artistic vision she brings to her work. Standing 5'10" with a graceful model-like figure from her earlier years in the industry, she moves with effortless confidence. Zendaya dresses in avant-garde outfits of her own design, turning heads with unexpected color combinations and structural elements. Her personality balances artistic sensitivity with business savvy, and she's known for her infectious laugh and ability to see beauty in unexpected places. Between international fashion weeks and designing her next collection, she seeks someone who appreciates art and culture, who can both support her creative journey and introduce new perspectives to inspire her work.`,

    name: "Zendaya Coleman",
    gender: "Female",
    age: "25",
    ethnicity: "Black/African American",
    sexual_orientation: "Straight",
    relationship_goal: "Taking Things Slow",
    body_type: "Slender",
    hair_color: "Black",
    hair_style: "Natural curls",
    personality: "Creative and Confident",
    clothing: "Avant-garde, self-designed outfits",
    occupation: "Fashion Designer",
    current_situation: "Building her brand",
    
    environment: "Art Gallery Opening",
    encounter_context: "Chance Encounter"
  },
  
  // International Journalist - Natalia
  "natalie": {
    bio: `Natalia Petrova, 31, is an award-winning international journalist known for her fearless reporting from conflict zones. With her striking platinum blonde hair typically pulled back in a practical bun, piercing blue eyes that seem to look right through you, and subtle Eastern European features, she has a memorable presence. Her athletic build comes from years of training for unpredictable field situations, giving her both strength and endurance. When not in field gear, Natalia favors sleek, minimalist clothing in neutral tones with statement accessories acquired during her global assignments. Fluent in five languages, she's equally comfortable in palace briefings or remote villages. Despite her tough exterior, close friends know her for her dry humor and surprising sentimentality about small kindnesses. Between assignments, she's looking for someone who understands her unpredictable schedule and passion for truth-telling, who can provide a sense of home no matter where in the world she returns from.`,

    name: "Natalia Petrova",
    gender: "Female",
    age: "31",
    ethnicity: "Russian",
    sexual_orientation: "Bisexual",
    relationship_goal: "Meaningful Connection",
    body_type: "Athletic",
    hair_color: "Platinum Blonde",
    hair_style: "Practical bun",
    personality: "Brave and Perceptive",
    clothing: "Sleek minimalist with statement accessories",
    occupation: "International Journalist",
    current_situation: "Between global assignments",
    
    environment: "Quiet Literary Cafe",
    encounter_context: "Professional Interview turned personal"
  },
  
  // Fitness Entrepreneur - Henry
  "henry": {
    bio: `Henry Fielding, 34, is the charismatic founder of a rapidly expanding fitness enterprise combining traditional training with cutting-edge sports science. With his broad shoulders, powerful build, and easy smile, he's the natural face of his brand. His dark hair is kept in a short, professional cut that highlights his strong jawline and intense brown eyes. At 6'2", his physique shows his commitment to his philosophy of functional strength and balanced wellness. Henry typically dresses in tailored athletic wear that bridges the gap between professional and fitness-ready. Despite his success, he maintains a down-to-earth approach, personally teaching classes and connecting with clients. His passion for helping others transform their lives stems from his own journey overcoming childhood health issues. Between opening new locations and developing new training programs, he's looking for someone who shares his active lifestyle but can also help him embrace moments of relaxation and appreciation for how far he's come.`,

    name: "Henry Fielding",
    gender: "Male",
    age: "34",
    ethnicity: "Mixed European",
    sexual_orientation: "Straight",
    relationship_goal: "Long-term Partnership",
    body_type: "Muscular",
    hair_color: "Dark Brown",
    hair_style: "Short professional cut",
    personality: "Charismatic and Driven",
    clothing: "Tailored athletic wear",
    occupation: "Fitness Entrepreneur",
    current_situation: "Expanding business nationally",
    
    environment: "High-end Health Club",
    encounter_context: "Personal Training Session"
  },
  
  // Marine Biologist - Chris
  "chris": {
    bio: `Chris Hemsworth, 30, is a marine biologist whose groundbreaking research on coral reef restoration has recently gained international attention. With sun-lightened dirty blonde hair often tousled from being in and out of water, bright blue eyes that crinkle when he smiles, and tan skin from days spent in the ocean, he has a natural, rugged appeal. His 6'3" frame carries a swimmer's build - broad shoulders, strong arms, and the lean physique of someone constantly in motion. Chris typically dresses casually in board shorts and scientific expedition t-shirts when working, upgrading to simple but quality button-downs and jeans for rare evenings out. His easygoing Australian charm belies a deeply analytical mind that can become completely absorbed in the underwater ecosystems he studies. His passion for ocean conservation is infectious, and he's happiest when sharing the wonders of marine life with others. Between research expeditions and grant proposals, he's looking for someone who appreciates both intellectual depth and simple pleasures, who might be willing to join him sometimes on his boat under star-filled skies far from shore.`,

    name: "Chris Hemsworth",
    gender: "Male",
    age: "30",
    ethnicity: "Australian",
    sexual_orientation: "Straight",
    relationship_goal: "Genuine Connection",
    body_type: "Athletic Swimmer's Build",
    hair_color: "Dirty Blonde",
    hair_style: "Tousled",
    personality: "Easygoing and Passionate",
    clothing: "Casual beachwear to simple button-downs",
    occupation: "Marine Biologist",
    current_situation: "Research breakthrough",
    
    environment: "Beachfront Restaurant",
    encounter_context: "Fundraising Event for Ocean Conservation"
  }
};

// Function to update bio text based on selection
function updateBioText() {
    const selectedBio = document.getElementById('predefinedBios').value;
    const bioTextArea = document.getElementById('bioTextArea');
    const bioText = document.getElementById('bioText');

    if (selectedBio && characterBios[selectedBio]) {
        bioTextArea.value = characterBios[selectedBio].bio;
        bioText.value = characterBios[selectedBio].bio;
    } else {
        bioTextArea.value = '';
        bioText.value = '';
    }
}

// Initialize when the document loads
document.addEventListener('DOMContentLoaded', function() {
    // Set up event listener for the bio selection
    const bioSelect = document.getElementById('predefinedBios');
    if (bioSelect) {
        bioSelect.addEventListener('change', updateBioText);
    }

    // Set up event listener for the textarea to update the hidden input
    const bioTextArea = document.getElementById('bioTextArea');
    const bioText = document.getElementById('bioText');
    if (bioTextArea && bioText) {
        bioTextArea.addEventListener('input', function() {
            bioText.value = bioTextArea.value;
        });
    }
});
