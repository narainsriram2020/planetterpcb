'use client';

import { BookOpen, Users, Star, GraduationCap, TrendingUp, HelpCircle } from 'lucide-react';

interface QuickStartProps {
  onExampleClick: (example: string) => void;
}

const examples = [
  {
    icon: BookOpen,
    title: 'Course Information',
    description: 'Get detailed course info',
    examples: [
      'Tell me about CMSC131',
      'What are the prerequisites for MATH140?',
      'Show me computer science courses'
    ],
    color: 'from-blue-500 to-blue-600'
  },
  {
    icon: Users,
    title: 'Professor Ratings',
    description: 'Find the best professors',
    examples: [
      'Who are the best professors for CMSC330?',
      'Tell me about Professor Nelson Padua-Perez',
      'Compare professors for MATH241'
    ],
    color: 'from-green-500 to-green-600'
  },
  {
    icon: Star,
    title: 'Grade Analytics',
    description: 'Check course difficulty',
    examples: [
      'What\'s the average GPA for CMSC131?',
      'Show me grade distributions for MATH140',
      'Which courses have the highest GPAs?'
    ],
    color: 'from-purple-500 to-purple-600'
  },
  {
    icon: GraduationCap,
    title: 'Academic Planning',
    description: 'Plan your academic path',
    examples: [
      'What courses should I take for CS major?',
      'Help me plan my semester',
      'What are the core requirements?'
    ],
    color: 'from-orange-500 to-orange-600'
  },
  {
    icon: TrendingUp,
    title: 'Course Recommendations',
    description: 'Get personalized suggestions',
    examples: [
      'Recommend easy courses for next semester',
      'What are the most popular CS courses?',
      'Suggest courses based on my interests'
    ],
    color: 'from-pink-500 to-pink-600'
  },
  {
    icon: HelpCircle,
    title: 'General Help',
    description: 'Ask anything about UMD',
    examples: [
      'How do I register for classes?',
      'What is the add/drop deadline?',
      'Tell me about UMD resources'
    ],
    color: 'from-indigo-500 to-indigo-600'
  }
];

export default function QuickStart({ onExampleClick }: QuickStartProps) {
  return (
    <div className="space-y-8">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">
          Welcome to PlanetTerp Chatbot! 🐢
        </h2>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Your intelligent guide to UMD courses, professors, and academic planning. 
          Ask me anything to get started!
        </p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {examples.map((category, index) => (
          <div key={index} className="bg-white rounded-xl shadow-lg border border-gray-100 p-6 hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
            <div className={`w-12 h-12 rounded-lg bg-gradient-to-r ${category.color} flex items-center justify-center mb-4`}>
              <category.icon className="w-6 h-6 text-white" />
            </div>
            
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {category.title}
            </h3>
            
            <p className="text-sm text-gray-600 mb-4">
              {category.description}
            </p>
            
            <div className="space-y-2">
              {category.examples.map((example, exampleIndex) => (
                <button
                  key={exampleIndex}
                  onClick={() => onExampleClick(example)}
                  className="w-full text-left p-3 text-sm text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors duration-200 hover:shadow-sm"
                >
                  &ldquo;{example}&rdquo;
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
