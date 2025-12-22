import { Building2 } from 'lucide-react'

function HeroCard() {
  return (
    <div className="bg-hero-gradient rounded-2xl p-8 text-white">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
          <Building2 size={24} />
        </div>
        <div>
          <h2 className="text-2xl font-bold mb-2">Serviceplan Policy Monitoring</h2>
          <p className="text-white/90 text-lg">
            AI-agent policy monitoring for legislation, regulations, speeches, and global political events.
          </p>
        </div>
      </div>
    </div>
  )
}

export default HeroCard
