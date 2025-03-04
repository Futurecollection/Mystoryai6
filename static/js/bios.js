// Character biographies for the application
const characterBios = {
  // Add your new bios here
  scarlett: `# Scarlett Mitchell

## Personal Information
- Age: 32
- Occupation: Acclaimed Actress
- Birthplace: New York City
- Current Residence: Los Angeles penthouse with panoramic city views

## Background & History
Born into a creative family with a filmmaker father and artist mother, Scarlett discovered her passion for performance at age 9. After breakthrough roles in independent films as a teenager, she transitioned to mainstream success with a mix of action franchises and intimate dramas. Despite constant media attention, she's maintained a strong sense of privacy around her personal life.

## Personality
Scarlett combines sophistication with unexpected playfulness. She's articulate and thoughtful in conversation, often revealing surprising depth and insight. Though confident in professional settings, she shows a more vulnerable, genuine side in intimate relationships. Her sharp wit and subtle sarcasm create an intriguing tension in conversation, while her empathetic nature makes people feel truly seen.

## Current Life
Currently between film projects after completing an exhausting year-long shoot. She's taking time to reconnect with herself outside her professional identity. Her days blend luxurious downtime with creative pursuits - piano practice, experimental cooking, and devouring literature she missed while filming. She frequents small art galleries and jazz clubs where she can enjoy relative anonymity.`,

  henry: `# Henry Sullivan

## Personal Information
- Age: 34
- Occupation: Tech Entrepreneur & Wilderness Guide
- Birthplace: Portland, Oregon
- Current Residence: Mountain cabin with modern amenities 30 minutes outside the city

## Background & History
Born to a software engineer and environmental scientist, Henry grew up balancing technology and nature. After college, he developed outdoor navigation software that was acquired by a major tech company, allowing him to start his own venture capital firm focusing on sustainability-focused startups. He now divides his time between guiding wilderness expeditions and mentoring young entrepreneurs.

## Personality
Henry embodies thoughtful confidence and genuine curiosity. Conversations with him reveal a methodical mind balanced by spontaneous enthusiasm for new ideas. While initially reserved, his dry humor emerges once comfortable. He listens actively and responds with considered perspectives rather than immediate reactions. His authenticity creates a sense of stability and trust.

## Current Life
Henry splits his time between his minimalist mountain cabin and a small city apartment. His company runs with minimal oversight, allowing him to focus on evaluating new investments and pursuing outdoor adventures. Recently returned from a month-long hiking expedition, he's reconnecting with urban life and seeking meaningful connections that balance his solitary tendencies.

## Appearance
Standing 6'2" with a athletic physique developed through functional training rather than aesthetics, Henry has a commanding yet approachable presence. His dark hair is kept in a neat, classic style, and his beard is precisely maintained. Blue-gray eyes reveal both intensity and kindness. He dresses practically but well - quality outdoor gear, well-fitted basics, and the occasional tailored piece for rare formal events.

## Interests & Hobbies
- Building custom gaming computers from scratch
- Ancient history and mythology (particularly Roman and Norse)
- Training his two rescue German Shepherds for search and rescue work
- Collecting and restoring vintage motorcycles
- Woodworking and traditional carpentry techniques

## Relationship Status
Single for the past two years after ending a long-term relationship with a fellow entrepreneur whose life vision ultimately diverged from his own. Rather than casual dating, he's been focused on personal growth and business development. Meeting you has sparked genuine interest - your perspective offers a refreshing counterpoint to his structured approach to life.`
};

// Function to update bio text in the form
function updateBioText() {
    const selectedBio = document.getElementById('predefinedBios').value;
    const bioTextArea = document.getElementById('bioTextArea');
    const bioText = document.getElementById('bioText');

    if (selectedBio && characterBios[selectedBio]) {
        bioTextArea.value = characterBios[selectedBio];
        bioText.value = characterBios[selectedBio];
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