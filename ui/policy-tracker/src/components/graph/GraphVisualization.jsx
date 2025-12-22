import { useState, useEffect, useRef, useCallback } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

// Node colors for different entity types
const NODE_COLORS = {
  // Primary types from Figma
  Risk: '#EC4899',
  Event: '#EF4444',
  Associations: '#10B981',
  Company: '#14B8A6',
  Law: '#3B82F6',
  Regulator: '#EC4899',
  Official: '#10B981',

  // Extended types
  Entity: '#c99286',
  Policy: '#aad3fa',
  Regulation: '#d0bfe1',
  Document: '#5bfff7',
  Person: '#97ad86',
  Organization: '#14B8A6',
  GovernmentAgency: '#00e3cf',
  LegislativeBody: '#8fd2ff',
  LegislativeProposal: '#ffa511',
  Politician: '#97ad86',
  PoliticalParty: '#bea978',
  Committee: '#9cc992',
  Vote: '#81b1ff',
  Jurisdiction: '#8da0d4',
  LegalFramework: '#6aafb3',
  ComplianceObligation: '#03ffc4',
  EnforcementAction: '#f9ae6d',
  TechnicalStandard: '#98c598',
  ConsultationProcess: '#7bbfdc',
  Industry: '#d294bc',
  Market: '#ff96b9',
  LobbyGroup: '#9cd28d',
  BusinessActivity: '#a8afd1',
  Exception: '#c487ce',

  // Fallback
  Unknown: '#888888',
}

function GraphVisualization({ graphData, onNodeClick, height = 500 }) {
  const fgRef = useRef()
  const [selectedNode, setSelectedNode] = useState(null)
  const [highlightNodes, setHighlightNodes] = useState(new Set())
  const [highlightLinks, setHighlightLinks] = useState(new Set())
  const [dimensions, setDimensions] = useState({ width: 800, height })
  const containerRef = useRef()

  // Update dimensions on resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height,
        })
      }
    }

    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [height])

  // Handle node click
  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node)

    // Highlight connected nodes and links
    const connectedNodeIds = new Set()
    const connectedLinkIds = new Set()

    graphData.links.forEach(link => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source
      const targetId = typeof link.target === 'object' ? link.target.id : link.target

      if (sourceId === node.id || targetId === node.id) {
        connectedNodeIds.add(sourceId)
        connectedNodeIds.add(targetId)
        connectedLinkIds.add(`${sourceId}-${targetId}`)
      }
    })

    setHighlightNodes(connectedNodeIds)
    setHighlightLinks(connectedLinkIds)

    // Center on node
    if (fgRef.current) {
      fgRef.current.centerAt(node.x, node.y, 500)
      fgRef.current.zoom(3, 500)
    }

    // Call parent handler
    if (onNodeClick) {
      onNodeClick(node)
    }
  }, [graphData, onNodeClick])

  // Handle node drag end - fix position
  const handleNodeDragEnd = useCallback((node) => {
    node.fx = node.x
    node.fy = node.y
  }, [])

  // Get node color
  const getNodeColor = useCallback((node) => {
    if (selectedNode && highlightNodes.size > 0) {
      return highlightNodes.has(node.id)
        ? NODE_COLORS[node.type] || NODE_COLORS.Unknown
        : '#cccccc'
    }
    return NODE_COLORS[node.type] || NODE_COLORS.Unknown
  }, [selectedNode, highlightNodes])

  // Get link color
  const getLinkColor = useCallback((link) => {
    const sourceId = typeof link.source === 'object' ? link.source.id : link.source
    const targetId = typeof link.target === 'object' ? link.target.id : link.target
    const linkId = `${sourceId}-${targetId}`

    if (selectedNode && highlightLinks.size > 0) {
      return highlightLinks.has(linkId) ? '#666666' : '#e5e5e5'
    }
    return '#999999'
  }, [selectedNode, highlightLinks])

  // Reset view
  const resetView = () => {
    setSelectedNode(null)
    setHighlightNodes(new Set())
    setHighlightLinks(new Set())

    // Unpin all nodes
    graphData.nodes.forEach(node => {
      node.fx = undefined
      node.fy = undefined
    })

    if (fgRef.current) {
      fgRef.current.zoomToFit(400)
    }
  }

  // Create a stable key for the graph based on data to force re-render when data changes
  const graphKey = `${graphData.nodes.length}-${graphData.links.length}-${graphData.nodes.map(n => n.id).join(',').slice(0, 100)}`

  return (
    <div ref={containerRef} className="w-full bg-white" style={{ height }}>
      <ForceGraph2D
        key={graphKey}
        ref={fgRef}
        graphData={graphData}
        width={dimensions.width}
        height={dimensions.height}
        nodeLabel={(node) => `${node.name}\nType: ${node.type}`}
        nodeColor={getNodeColor}
        nodeRelSize={6}
        nodeVal={(node) => node.val || 1}
        linkColor={getLinkColor}
        linkWidth={(link) => {
          const sourceId = typeof link.source === 'object' ? link.source.id : link.source
          const targetId = typeof link.target === 'object' ? link.target.id : link.target
          return highlightLinks.has(`${sourceId}-${targetId}`) ? 2 : 1
        }}
        linkDirectionalParticles={1}
        linkDirectionalParticleWidth={2}
        onNodeClick={handleNodeClick}
        onNodeDragEnd={handleNodeDragEnd}
        onBackgroundClick={resetView}
        backgroundColor="#ffffff"
        nodeCanvasObject={(node, ctx, globalScale) => {
          // Draw node circle
          const size = (node.val || 1) * 3
          ctx.beginPath()
          ctx.arc(node.x, node.y, size, 0, 2 * Math.PI)
          ctx.fillStyle = getNodeColor(node)
          ctx.fill()

          // Draw label
          const label = node.name
          const fontSize = Math.max(10 / globalScale, 2)
          ctx.font = `${fontSize}px Inter, sans-serif`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillStyle = '#333333'
          ctx.fillText(label, node.x, node.y + size + fontSize)
        }}
        nodeCanvasObjectMode={() => 'replace'}
        cooldownTicks={100}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
      />
    </div>
  )
}

export default GraphVisualization
