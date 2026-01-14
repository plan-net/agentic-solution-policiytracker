import { useState, useEffect, useRef, useCallback } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import ForceGraph3D from 'react-force-graph-3d'
import SpriteText from 'three-spritetext'
import * as THREE from 'three'

// Node colors from Neo4j Browser style (.grass file)
const NODE_COLORS = {
  // Core entity types
  Entity: '#c99286',
  Policy: '#aad3fa',
  Regulation: '#d0bfe1',
  Document: '#5bfff7',
  Person: '#abaa86',
  Company: '#ffbfb5',

  // Government & Political
  GovernmentAgency: '#00e3cf',
  LegislativeBody: '#8fd2ff',
  LegislativeProposal: '#ffa511',
  Politician: '#97ad86',
  PoliticalParty: '#bea978',
  Committee: '#9cc992',
  Vote: '#81b1ff',
  Jurisdiction: '#8da0d4',

  // Legal & Compliance
  LegalFramework: '#6aafb3',
  ComplianceObligation: '#03ffc4',
  EnforcementAction: '#f9ae6d',
  TechnicalStandard: '#98c598',
  ConsultationProcess: '#7bbfdc',

  // Business & Industry
  Industry: '#d294bc',
  Market: '#ff96b9',
  LobbyGroup: '#9cd28d',
  BusinessActivity: '#a8afd1',
  Exception: '#c487ce',

  // German Parliament (Bundestag)
  Drucksache: '#3cc5f2',
  Sachgebiet: '#21ebbd',
  Deskriptor: '#61dbff',
  Vorgang: '#fae353',
  BundestagPerson: '#ff8d64',
  Fraktion: '#5dd759',
  BundestagFraktion: '#87fd92',
  Wahlperiode: '#1946f6',
  Plenarprotokoll: '#f7a9cb',
  Vorgangsposition: '#b3a784',
  Aktivitaet: '#a7a884',
  DrucksachePage: '#ffc4f4',

  // Other types
  ChatSession: '#7fddbf',
  Community: '#7cc2ff',
  EntityAlias: '#ffd0d3',
  CanonicalEntity: '#ff657b',
  Episodic: '#3fa5f5',

  // Fallback for unknown types
  Unknown: '#888888'
}

function GraphVisualization({ graphData, is3D = false, onNodeClick = null, height = 600 }) {
  const [viewMode, setViewMode] = useState(is3D ? '3d' : '2d')
  const [autoRotate, setAutoRotate] = useState(false)
  const [selectedNode, setSelectedNode] = useState(null)
  const [selectedLink, setSelectedLink] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [highlightNodes, setHighlightNodes] = useState(new Set())
  const [highlightLinks, setHighlightLinks] = useState(new Set())
  const [graphWidth, setGraphWidth] = useState(typeof window !== 'undefined' ? window.innerWidth - 100 : 800)
  const fgRef = useRef()

  // Update graph width on window resize
  useEffect(() => {
    const handleResize = () => {
      setGraphWidth(window.innerWidth - 100)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Filter nodes based on search and validate links
  const filteredData = useCallback(() => {
    // First, get all valid node IDs from the graph data
    const allNodeIds = new Set(graphData.nodes.map(n => n.id))

    // Filter links to only include those where both source and target exist in nodes
    // This prevents react-force-graph from silently dropping links with missing endpoints
    const validLinks = graphData.links.filter(link => {
      const sourceId = link.source.id || link.source
      const targetId = link.target.id || link.target
      const isValid = allNodeIds.has(sourceId) && allNodeIds.has(targetId)
      if (!isValid) {
        console.warn(`Orphaned link filtered out: ${sourceId} -> ${targetId} (missing node)`)
      }
      return isValid
    })

    // Log if any links were filtered out
    if (validLinks.length !== graphData.links.length) {
      console.warn(`Filtered ${graphData.links.length - validLinks.length} orphaned links (${validLinks.length} valid of ${graphData.links.length} total)`)
    }

    if (!searchTerm) {
      return {
        nodes: graphData.nodes,
        links: validLinks
      }
    }

    const term = searchTerm.toLowerCase()
    const matchingNodes = graphData.nodes.filter(node =>
      node.name.toLowerCase().includes(term) ||
      node.type.toLowerCase().includes(term)
    )
    const matchingNodeIds = new Set(matchingNodes.map(n => n.id))

    // Include links connected to matching nodes (already validated)
    const matchingLinks = validLinks.filter(link =>
      matchingNodeIds.has(link.source.id || link.source) ||
      matchingNodeIds.has(link.target.id || link.target)
    )

    return {
      nodes: matchingNodes,
      links: matchingLinks
    }
  }, [graphData, searchTerm])

  // Auto-rotate in 3D mode
  useEffect(() => {
    if (viewMode === '3d' && autoRotate && fgRef.current) {
      const interval = setInterval(() => {
        const camera = fgRef.current.camera()
        const controls = fgRef.current.controls()
        if (controls) {
          controls.autoRotate = true
          controls.autoRotateSpeed = 0.5
          controls.update()
        }
      }, 16)
      return () => clearInterval(interval)
    }
  }, [viewMode, autoRotate])

  // Node click handler
  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node)
    setSelectedLink(null)  // Clear selected link when clicking a node
    if (onNodeClick) {
      onNodeClick(node)
    }

    // Highlight connected nodes and links
    const connectedNodeIds = new Set()
    const connectedLinkIds = new Set()

    graphData.links.forEach(link => {
      const sourceId = link.source.id || link.source
      const targetId = link.target.id || link.target

      if (sourceId === node.id || targetId === node.id) {
        connectedNodeIds.add(sourceId)
        connectedNodeIds.add(targetId)
        connectedLinkIds.add(`${sourceId}-${targetId}`)
      }
    })

    setHighlightNodes(connectedNodeIds)
    setHighlightLinks(connectedLinkIds)

    // Center camera on node
    if (fgRef.current) {
      if (viewMode === '3d') {
        fgRef.current.centerAt(node.x, node.y, node.z, 1000)
        fgRef.current.zoom(8, 1000)
      } else {
        fgRef.current.centerAt(node.x, node.y, 1000)
        fgRef.current.zoom(4, 1000)
      }
    }
  }, [graphData, onNodeClick, viewMode])

  // Handle node drag end - fix node position
  const handleNodeDragEnd = useCallback((node) => {
    // Fix node position by setting fx, fy (and fz for 3D)
    node.fx = node.x
    node.fy = node.y
    if (viewMode === '3d') {
      node.fz = node.z
    }
  }, [viewMode])

  // Link click handler
  const handleLinkClick = useCallback((link) => {
    setSelectedLink(link)
    setSelectedNode(null)  // Clear selected node when clicking a link

    // Get source and target node names (safely handle both object and string formats)
    const sourceName = typeof link.source === 'object'
      ? (link.source.name || link.source.id)
      : link.source
    const targetName = typeof link.target === 'object'
      ? (link.target.name || link.target.id)
      : link.target

    console.log(`Link clicked: ${sourceName} --[${link.type || 'RELATED_TO'}]--> ${targetName}`)
  }, [])

  // Reset view
  const handleResetView = () => {
    setSelectedNode(null)
    setSelectedLink(null)
    setHighlightNodes(new Set())
    setHighlightLinks(new Set())
    setSearchTerm('')

    // Unpin all nodes (remove fixed positions)
    graphData.nodes.forEach(node => {
      node.fx = undefined
      node.fy = undefined
      node.fz = undefined
    })

    if (fgRef.current) {
      fgRef.current.zoomToFit(400)
    }
  }

  // Node color based on type
  const getNodeColor = (node) => {
    if (selectedNode && highlightNodes.size > 0) {
      return highlightNodes.has(node.id) ? NODE_COLORS[node.type] || NODE_COLORS.Entity : '#555'
    }
    return NODE_COLORS[node.type] || NODE_COLORS.Entity
  }

  // Node label
  const getNodeLabel = (node) => {
    return `${node.name}\nType: ${node.type}\nConnections: ${node.val || 0}`
  }

  // Link color
  const getLinkColor = (link) => {
    const sourceId = link.source.id || link.source
    const targetId = link.target.id || link.target
    const linkId = `${sourceId}-${targetId}`

    if (selectedNode && highlightLinks.size > 0) {
      return highlightLinks.has(linkId) ? '#ffffff' : '#666666'
    }
    return '#ffffff'  // Bright white for better visibility against black background
  }

  // 3D node object - text label only (sphere is handled by default rendering)
  const nodeThreeObject = useCallback((node) => {
    const sprite = new SpriteText(node.name)
    sprite.material.depthWrite = false  // Make sprite render above spheres
    sprite.color = '#ffffff'  // White text
    sprite.backgroundColor = '#404040'  // Dark grey background
    sprite.padding = 4
    sprite.borderRadius = 4
    sprite.borderWidth = 1
    sprite.borderColor = '#666666'
    sprite.textHeight = 4
    sprite.fontWeight = 'bold'
    return sprite
  }, [selectedNode, highlightNodes])

  // 3D link object - text label for relationship type
  const linkThreeObject = useCallback((link) => {
    const sprite = new SpriteText(link.type || 'RELATED_TO')
    sprite.color = '#ffcc00'  // Yellow/gold text for visibility
    sprite.backgroundColor = 'rgba(0, 0, 0, 0.6)'  // Semi-transparent dark background
    sprite.padding = 2
    sprite.borderRadius = 2
    sprite.textHeight = 2
    sprite.fontWeight = 'normal'
    return sprite
  }, [])

  // 3D link position update - position label at midpoint of link
  const linkPositionUpdate = useCallback((sprite, { start, end }) => {
    const midPoint = Object.assign(...['x', 'y', 'z'].map(c => ({
      [c]: start[c] + (end[c] - start[c]) / 2
    })))
    Object.assign(sprite.position, midPoint)
  }, [])

  const data = filteredData()

  // Debug: Log data
  console.log('GraphVisualization render:', {
    nodeCount: data.nodes.length,
    linkCount: data.links.length,
    selectedNode,
    selectedLink
  })

  return (
    <div className="relative">
      {/* Controls Bar */}
      <div className="flex items-center justify-between mb-4 p-3 bg-gray-800 rounded-lg">
        {/* View Mode Toggle */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">View:</span>
          <button
            onClick={() => setViewMode('2d')}
            className={`px-3 py-1 text-sm rounded transition-colors ${
              viewMode === '2d'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            2D Canvas
          </button>
          <button
            onClick={() => setViewMode('3d')}
            className={`px-3 py-1 text-sm rounded transition-colors ${
              viewMode === '3d'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            3D View 🎮
          </button>
        </div>

        {/* 3D Controls */}
        {viewMode === '3d' && (
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRotate}
                onChange={(e) => setAutoRotate(e.target.checked)}
                className="rounded"
              />
              Auto-rotate
            </label>
          </div>
        )}

        {/* Search */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-3 py-1 bg-gray-700 text-gray-200 text-sm rounded border border-gray-600 focus:border-blue-500 focus:outline-none w-48"
          />
          <button
            onClick={handleResetView}
            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-sm rounded transition-colors"
            title="Reset view"
          >
            🔄 Reset
          </button>
        </div>
      </div>

      {/* Graph Stats */}
      <div className="flex items-center gap-4 mb-3 text-sm text-gray-400">
        <span>📊 {data.nodes.length} nodes</span>
        <span>🔗 {data.links.length} edges</span>
        {selectedNode && (
          <span className="text-blue-400">
            👆 Selected Node: {selectedNode.name}
          </span>
        )}
        {selectedLink && (
          <span className="text-yellow-400">
            👆 Selected Link: {selectedLink.type || 'RELATED_TO'}
          </span>
        )}
      </div>

      {/* Graph Visualization */}
      <div className="bg-gray-950 rounded-lg overflow-hidden border border-gray-800">
        {viewMode === '2d' ? (
          <ForceGraph2D
            ref={fgRef}
            graphData={data}
            width={graphWidth}
            height={height}
            nodeLabel={getNodeLabel}
            nodeColor={getNodeColor}
            nodeRelSize={6}
            nodeVal={node => node.val || 1}
            linkColor={getLinkColor}
            linkWidth={link => (highlightLinks.has(`${link.source.id || link.source}-${link.target.id || link.target}`) ? 2 : 1)}
            linkDirectionalParticles={2}
            linkDirectionalParticleWidth={link => (highlightLinks.has(`${link.source.id || link.source}-${link.target.id || link.target}`) ? 2 : 0)}
            onNodeClick={handleNodeClick}
            onNodeDragEnd={handleNodeDragEnd}
            onLinkClick={handleLinkClick}
            backgroundColor="#000000"
            nodeCanvasObject={(node, ctx, globalScale) => {
              const label = node.name
              const fontSize = 12 / globalScale
              ctx.font = `${fontSize}px Sans-Serif`
              ctx.textAlign = 'center'
              ctx.textBaseline = 'middle'
              ctx.fillStyle = 'rgba(255, 255, 255, 0.8)'
              ctx.fillText(label, node.x, node.y + 10)
            }}
            nodeCanvasObjectMode={() => 'after'}
            linkCanvasObject={(link, ctx, globalScale) => {
              const label = link.type || 'RELATED_TO'
              const fontSize = 10 / globalScale
              ctx.font = `${fontSize}px Sans-Serif`
              ctx.textAlign = 'center'
              ctx.textBaseline = 'middle'

              // Get link coordinates
              const start = link.source
              const end = link.target

              if (typeof start !== 'object' || typeof end !== 'object') return

              // Calculate midpoint
              const midX = start.x + (end.x - start.x) / 2
              const midY = start.y + (end.y - start.y) / 2

              // Draw background rectangle for better readability
              const padding = 2
              const textWidth = ctx.measureText(label).width
              ctx.fillStyle = 'rgba(0, 0, 0, 0.7)'
              ctx.fillRect(
                midX - textWidth / 2 - padding,
                midY - fontSize / 2 - padding,
                textWidth + padding * 2,
                fontSize + padding * 2
              )

              // Draw text
              ctx.fillStyle = '#ffcc00'  // Yellow/gold color for relationship labels
              ctx.fillText(label, midX, midY)
            }}
            linkCanvasObjectMode={() => 'after'}
          />
        ) : (
          <ForceGraph3D
            ref={fgRef}
            graphData={data}
            width={graphWidth}
            height={height}
            nodeLabel={getNodeLabel}
            nodeColor={getNodeColor}
            nodeRelSize={6}
            nodeVal={node => node.val || 1}
            nodeThreeObject={nodeThreeObject}
            nodeThreeObjectExtend={true}
            linkColor={getLinkColor}
            linkWidth={link => (highlightLinks.has(`${link.source.id || link.source}-${link.target.id || link.target}`) ? 2 : 1)}
            linkDirectionalParticles={2}
            linkDirectionalParticleWidth={link => (highlightLinks.has(`${link.source.id || link.source}-${link.target.id || link.target}`) ? 2 : 0)}
            linkThreeObject={linkThreeObject}
            linkThreeObjectExtend={true}
            linkPositionUpdate={linkPositionUpdate}
            onNodeClick={handleNodeClick}
            onNodeDragEnd={handleNodeDragEnd}
            onLinkClick={handleLinkClick}
            backgroundColor="#000000"
            enableNodeDrag={true}
            enableNavigationControls={true}
            showNavInfo={false}
          />
        )}
      </div>

      {/* Legend */}
      <div className="mt-4 p-3 bg-gray-800 rounded-lg">
        <div className="text-sm font-medium text-gray-300 mb-2">Entity Types:</div>
        <div className="flex flex-wrap gap-3">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: color }}
              ></div>
              <span className="text-sm text-gray-400">{type}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Selected Node Details */}
      {selectedNode && (
        <div className="mt-4 p-4 bg-gray-800 rounded-lg border border-blue-500">
          <div className="flex items-start justify-between mb-2">
            <h3 className="text-lg font-semibold text-blue-400">{selectedNode.name}</h3>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-gray-400 hover:text-white"
            >
              ✕
            </button>
          </div>
          <div className="space-y-2 text-sm">
            <div>
              <span className="text-gray-400">Type:</span>{' '}
              <span className="text-gray-200">{selectedNode.type}</span>
            </div>
            <div>
              <span className="text-gray-400">ID:</span>{' '}
              <span className="text-gray-200 font-mono text-xs">{selectedNode.id}</span>
            </div>
            {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
              <div>
                <span className="text-gray-400">Properties:</span>
                <pre className="mt-1 p-2 bg-gray-900 rounded text-xs overflow-auto max-h-32">
                  {JSON.stringify(selectedNode.properties, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Selected Relationship Details */}
      {selectedLink && (
        <div className="mt-4 p-4 bg-gray-800 rounded-lg border border-yellow-500">
          <div className="flex items-start justify-between mb-2">
            <h3 className="text-lg font-semibold text-yellow-400">
              {selectedLink.type || 'RELATED_TO'}
            </h3>
            <button
              onClick={() => setSelectedLink(null)}
              className="text-gray-400 hover:text-white"
            >
              ✕
            </button>
          </div>
          <div className="space-y-2 text-sm">
            <div>
              <span className="text-gray-400">Relationship:</span>{' '}
              <div className="mt-1 p-2 bg-gray-900 rounded">
                <span className="text-blue-400">
                  {(typeof selectedLink.source === 'object' ? selectedLink.source.name || selectedLink.source.id : selectedLink.source) || 'Unknown'}
                </span>
                {' '}
                <span className="text-yellow-400">--[{selectedLink.type || 'RELATED_TO'}]--&gt;</span>
                {' '}
                <span className="text-green-400">
                  {(typeof selectedLink.target === 'object' ? selectedLink.target.name || selectedLink.target.id : selectedLink.target) || 'Unknown'}
                </span>
              </div>
            </div>
            <div>
              <span className="text-gray-400">Source ID:</span>{' '}
              <span className="text-gray-200 font-mono text-xs">
                {typeof selectedLink.source === 'object' ? selectedLink.source.id : selectedLink.source}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Target ID:</span>{' '}
              <span className="text-gray-200 font-mono text-xs">
                {typeof selectedLink.target === 'object' ? selectedLink.target.id : selectedLink.target}
              </span>
            </div>
            {selectedLink.properties && Object.keys(selectedLink.properties).length > 0 && (
              <div>
                <span className="text-gray-400">Properties:</span>
                <pre className="mt-1 p-2 bg-gray-900 rounded text-xs overflow-auto max-h-32">
                  {JSON.stringify(selectedLink.properties, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default GraphVisualization
