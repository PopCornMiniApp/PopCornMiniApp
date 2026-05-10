import React from 'react';
import { Users, Lock, Video, Mic } from 'lucide-react';

interface RoomCardProps {
  room: {
    room_id: string;
    name: string;
    description: string;
    host_user_id: number;
    content_type: string;
    is_public: boolean;
    has_password: boolean;
    max_participants: number;
    participant_count: number;
    status: string;
    voice_chat_enabled: boolean;
    sync_mode: string;
  };
  onJoin: (roomId: string) => void;
}

const RoomCard: React.FC<RoomCardProps> = ({ room, onJoin }) => {
  const getStatusColor = () => {
    switch (room.status) {
      case 'playing':
        return 'bg-green-500';
      case 'paused':
        return 'bg-yellow-500';
      case 'waiting':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getSyncModeLabel = () => {
    switch (room.sync_mode) {
      case 'host_control':
        return 'Host Control';
      case 'watch_party':
        return 'Watch Party';
      case 'free_watch':
        return 'Free Watch';
      case 'voting':
        return 'Voting';
      default:
        return room.sync_mode;
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 hover:bg-gray-750 transition-colors cursor-pointer"
         onClick={() => onJoin(room.room_id)}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-white mb-1">{room.name}</h3>
          {room.description && (
            <p className="text-sm text-gray-400 line-clamp-2">{room.description}</p>
          )}
        </div>
        <div className={`w-3 h-3 rounded-full ${getStatusColor()} ml-2 mt-1`} />
      </div>

      <div className="flex items-center gap-4 text-sm text-gray-400 mb-3">
        <div className="flex items-center gap-1">
          <Users size={16} />
          <span>{room.participant_count}/{room.max_participants}</span>
        </div>
        
        {!room.is_public && (
          <div className="flex items-center gap-1">
            <Lock size={16} />
            <span>Private</span>
          </div>
        )}
        
        {room.voice_chat_enabled && (
          <div className="flex items-center gap-1">
            <Mic size={16} />
            <span>Voice</span>
          </div>
        )}
        
        <div className="flex items-center gap-1">
          <Video size={16} />
          <span className="capitalize">{room.content_type}</span>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">{getSyncModeLabel()}</span>
        <span className="text-xs text-gray-500 capitalize">{room.status}</span>
      </div>
    </div>
  );
};

export default RoomCard;

// Made with Bob
